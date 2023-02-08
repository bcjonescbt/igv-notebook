from ipywidgets import widgets, Button, Dropdown, SelectionSlider, SelectMultiple, HBox, VBox, Layout
import pybedtools

import matplotlib.cm as cm

class NavBox:
    ROI_BUFFER_BP=20000
    
    def __init__(self, browser, roi_key, init_roi_index=0, chr_size_file=None):
        self._browser = browser
        self._roi_key = roi_key
        self._roi = pybedtools.BedTool(self._roi_key['path'][init_roi_index])
        
        if chr_size_file:
            self._store_chr_sizes(chr_size_file)
            self._roi = self._roi.slop(genome=self._chrome_size_dict, b=self.ROI_BUFFER_BP)

        # build navigation interfact
        self._chr_dropdown = Dropdown(options=self._get_chr_list(), description="Chr:", value='1',
                                      layout=Layout(width='20%', height='25px'))
        self._chr_dropdown.observe(self._chr_dropdown_change, 'value')
        
        self._slider = SelectionSlider(options=self._get_slider_ranges(), continuous_update=False,
                                      layout=Layout(width='70%', height='30px'))
        self._slider.observe(self._slider_change, 'value')

        self._nav_dropdown = Dropdown(options=self._roi_key.name.values, description="Nav:", 
                                      layout=Layout(width='30%', height='25px'))
        self._nav_dropdown.observe(self._nav_dropdown_change, 'value')
        
        self._roi_select = SelectMultiple(options=self._roi_key.name.values, value=(), description="ROIs")
        self._roi_select.observe(self._roi_select_change, 'value')

        # Icons from https://fontawesome.com/v4/icons/
        button_layout = Layout(width='8%', height='30px')
        self._button_fwd = Button(tooltip="Fwd", icon='forward', layout=button_layout)
        self._button_back = Button(tooltip="Back", icon='backward', layout=button_layout)
        self._button_fast_fwd = Button(tooltip="Fast Fwd", icon='fast-forward', layout=button_layout)
        self._button_fast_back = Button(tooltip="Fast Back", icon='fast-backward', layout=button_layout)

        self._button_fwd.on_click(self._button_press)
        self._button_back.on_click(self._button_press)
        self._button_fast_fwd.on_click(self._button_press)
        self._button_fast_back.on_click(self._button_press)

        box_layout = Layout(flex_flow='row', justify_content='center', width='100%')
        display(HBox((VBox((
                        HBox((self._chr_dropdown, self._slider), layout=box_layout),
                        HBox((self._nav_dropdown, self._button_fast_back, self._button_back, 
                              self._button_fwd, self._button_fast_fwd), layout=box_layout)
                        ), layout=Layout(width='90%')), 
                    self._roi_select), layout=box_layout))

    def set_nav_roi(self, roi):
        self._roi = roi

        if self._chrome_size_dict:
            self._roi = self._roi.slop(genome=self._chrome_size_dict, b=self.ROI_BUFFER_BP)
            
        self._chr_dropdown.options=self._get_chr_list()
        self._chr_dropdown.value=self._chr_dropdown.options[0]
        self._slider.options = self._get_slider_ranges()

    def _slider_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_locus = f"chr{self._chr_dropdown.value}:{self._slider.value}"
            print("Locus changed to %s" % new_locus)
            self._browser.search(new_locus)

    def _chr_dropdown_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            self._slider.options = self._get_slider_ranges()
            
    def _nav_dropdown_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            print(f"New Nav ROI: {self._roi_key['path'][self._nav_dropdown.index]}")
            self.set_nav_roi(pybedtools.BedTool(self._roi_key['path'][self._nav_dropdown.index]))
            
    def _roi_select_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            self._browser.clear_rois()

            print(f"New ROIs: {self._roi_select.index}")
            cmap = cm.get_cmap('Set3')

            roi_list = []
            for i in self._roi_select.index:
                key = roi_key.iloc[i]
                roi_list.append({'name': key['name'], 'url': key['path_igv'], 
                                 'color': "rgba(" + ','.join([str(int(c*255)) for c in cmap.colors[-1-i]]) + ",0.25)"})
            self._browser.load_roi(roi_list)
            
    def _button_press(self, b):
        options = self._slider.options

        if b.tooltip == "Fwd":
            delta = +1
        elif b.tooltip == "Back":
            delta = -1
        elif b.tooltip == "Fast Fwd":
            delta = +int(len(options) * 0.10)
        elif b.tooltip == "Fast Back":
            delta = -int(len(options) * 0.10)
            
        new_index = min(len(options)-1, max(0, self._slider.index + delta))
        self._slider.index = new_index

    def _get_chr_list(self):
        # get the list of chr
        chr_list = [str(x) for x in range(1, 23)]
        chr_list.extend([x for x in set(f[0] for f in self._roi) if x[0] in ('X', 'Y')])
        return chr_list

    def _get_slider_ranges(self):
        return [f"{int(f[1]):,d}-{int(f[2]):,d}" for f in self._roi.filter(lambda x: x[0] == self._chr_dropdown.value)]
    
    def _store_chr_sizes(self, chr_size_file):
        self._chrome_size_dict = {}
        with open(chr_size_file) as f:
            for line in f:
                (key, value) = line.split()
                self._chrome_size_dict[key] = (0, value)
