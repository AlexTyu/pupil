'''
(*)~----------------------------------------------------------------------------------
 Pupil - eye tracking platform
 Copyright (C) 2012-2015  Pupil Labs

 Distributed under the terms of the CC BY-NC-SA License.
 License details are in the file license.txt, distributed as part of this software.
----------------------------------------------------------------------------------~(*)
'''
import os
from pyglui import ui
from plugin import Plugin
from file_methods import load_object,save_object

import numpy as np
from OpenGL.GL import *
from glfw import glfwGetWindowSize,glfwGetCurrentContext
from pyglui.cygl.utils import draw_polyline,RGBA
from pyglui.pyfontstash import fontstash
from pyglui.ui import get_opensans_font_path

#logging
import logging
logger = logging.getLogger(__name__)

class Annotation_Capture(Plugin):
    """Describe your plugin here
    """
    def __init__(self,g_pool,annotations=[('My annoation','e')]):
        super(Annotation_Capture, self).__init__(g_pool)
        self.menu = None
        self.sub_menu = None
        self.buttons = []

        self.annotations = annotations[:]

        self.new_annotation_name = 'new annotation name'
        self.new_annotation_hotkey = 'e'

        self.current_frame = -1

    def init_gui(self):
        #lets make a menu entry in the sidebar
        self.menu = ui.Growing_Menu('Add annoations')
        self.g_pool.sidebar.append(self.menu)

        #add a button to close the plugin
        self.menu.append(ui.Button('close',self.close))
        self.menu.append(ui.Text_Input('new_annotation_name',self))
        self.menu.append(ui.Text_Input('new_annotation_hotkey',self))
        self.menu.append(ui.Button('add annotation type',self.add_annotation))
        self.sub_menu = ui.Growing_Menu('Events - click to remove')
        self.menu.append(self.sub_menu)
        self.update_buttons()


    def update_buttons(self):
        for b in self.buttons:
            self.g_pool.quickbar.remove(b)
            self.sub_menu.elements[:] = []
        self.buttons = []

        for e_name,hotkey in self.annotations:

            def make_fire(e_name,hotkey):
                return lambda _ : self.fire_annotation(e_name)

            def make_remove(e_name,hotkey):
                return lambda: self.remove_annotation((e_name,hotkey))

            thumb = ui.Thumb(e_name,setter=make_fire(e_name,hotkey), getter=lambda: False,
            label=hotkey,hotkey=hotkey)
            self.buttons.append(thumb)
            self.g_pool.quickbar.append(thumb)
            self.sub_menu.append(ui.Button(e_name+" <"+hotkey+">",make_remove(e_name,hotkey)))



    def deinit_gui(self):
        if self.menu:
            self.g_pool.sidebar.remove(self.menu)
            self.menu = None
        if self.buttons:
            for b in self.buttons:
                self.g_pool.quickbar.remove(b)
            self.buttons = []

    def add_annotation(self):
        self.annotations.append((self.new_annotation_name,self.new_annotation_hotkey))
        self.update_buttons()

    def remove_annotation(self,annotation):
        self.annotations.remove(annotation)
        self.update_buttons()

    def close(self):
        self.alive = False

    def fire_annotation(self,annotation_label):
        t = self.g_pool.capture.get_timestamp()
        logger.info('"%s"@%s'%(annotation_label,t))
        notification = {'subject':'annotation','label':annotation_label,'timestamp':t,'duration':0.0,'source':'local','network_propagate':True,'record':True} #you may add more field to this dictionary if you want.
        self.notify_all(notification)


    def get_init_dict(self):
        return {'annotations':self.annotations}

    def cleanup(self):
        """ called when the plugin gets terminated.
        This happens either voluntarily or forced.
        if you have a GUI or glfw window destroy it here.
        """
        self.deinit_gui()


class Annotation_Player(Annotation_Capture):
    """Describe your plugin here
    View,edit and add Annotations.
    """
    def __init__(self,g_pool,annotations=None):
        if annotations:
            super(Annotation_Player, self).__init__(g_pool,annotations)
        else:
            super(Annotation_Player, self).__init__(g_pool)

        from player_methods import correlate_data

        self.frame_count = len(self.g_pool.timestamps)

        #display layout
        self.padding = 20. #in sceen pixel
        self.window_size = 0,0


        #first we try to load annoations previously saved with pupil player
        try:
            annotations_list = load_object(os.path.join(self.g_pool.rec_dir, "annotations"))
        except IOError as e:
            #if that fails we assume this is the first time this recording is played and we load annotations from pupil_data
            try:
                notifications_list = load_object(os.path.join(self.g_pool.rec_dir, "pupil_data"))['notifications']
                annotations_list = [n for n in notifications_list if n['subject']=='annotation']
            except (KeyError,IOError) as e:
                annotations_list = []
                logger.debug('No annotations found in pupil_data file.')
            else:
                logger.debug('loaded %s annotations from pupil_data file'%len(annotations_list))
        else:
            logger.debug('loaded %s annotations from annotations file'%len(annotations_list))

        self.annotations_by_frame = correlate_data(annotations_list, self.g_pool.timestamps)
        self.annotations_list = annotations_list

    def init_gui(self):
        #lets make a menu entry in the sidebar
        self.menu = ui.Scrolling_Menu('view add edit annoations')
        self.g_pool.gui.append(self.menu)

        #add a button to close the plugin
        self.menu.append(ui.Button('close',self.close))
        self.menu.append(ui.Text_Input('new_annotation_name',self))
        self.menu.append(ui.Text_Input('new_annotation_hotkey',self))
        self.menu.append(ui.Button('add annotation type',self.add_annotation))
        self.sub_menu = ui.Growing_Menu('Events - click to remove')
        self.menu.append(self.sub_menu)
        self.update_buttons()


        self.on_window_resize(glfwGetCurrentContext(),*glfwGetWindowSize(glfwGetCurrentContext()))

        self.glfont = fontstash.Context()
        self.glfont.add_font('opensans',get_opensans_font_path())
        self.glfont.set_size(24)
        #self.glfont.set_color_float((0.2,0.5,0.9,1.0))
        self.glfont.set_align_string(v_align='center',h_align='middle')


    def on_window_resize(self,window,w,h):
        self.window_size = w,h
        self.h_pad = self.padding * self.frame_count/float(w)
        self.v_pad = self.padding * 1./h

    def fire_annotation(self,annotation_label):
        t = self.g_pool.capture.get_timestamp()
        logger.info('"%s"@%s'%(annotation_label,t))
        notification = {'subject':'annotation','label':annotation_label,'timestamp':t,'duration':0.0,'source':'local','added_in_player':True,'index':self.g_pool.capture.get_frame_index()-1} #you may add more field to this dictionary if you want.
        self.annotations_list.append(notification)
        self.annotations_by_frame[notification['index']].append(notification)


    def update(self,frame,events):
        if frame.index != self.current_frame:
            self.current_frame = frame.index
            events = self.annotations_by_frame[frame.index]
            for e in events:
                logger.info(str(e))

    def deinit_gui(self):
        if self.menu:
            self.g_pool.gui.remove(self.menu)
            self.menu = None


    def unset_alive(self):
        self.alive = False


    def gl_display(self):
        #TODO: implement this
        pass

    def cleanup(self):
        """called when the plugin gets terminated.
        This happens either voluntarily or forced.
        if you have a GUI or glfw window destroy it here.
        """
        self.deinit_gui()
        save_object(self.annotations_list,os.path.join(self.g_pool.rec_dir, "annotations"))
