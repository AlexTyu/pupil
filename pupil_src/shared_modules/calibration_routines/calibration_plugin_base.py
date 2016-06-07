from plugin import Plugin


class Calibration_Plugin(Plugin):
    '''base class for all calibration routines'''
    uniqueness = 'by_base_class'
    def __init__(self,g_pool):
        super(Calibration_Plugin, self).__init__(g_pool)
        self.g_pool.active_calibration_plugin = self
        self.pupil_confidence_threshold = 0.6
        self.active = False

    def on_notify(self,notification):
        if notification['subject'].startswith('calibration.should_start'):
            if self.active:
                logger.warning('Calibration already running.')
            else:
                self.start()
        elif notification['subject'].startswith('calibration.should_stop'):
            if self.active:
                self.stop()
            else:
                logger.warning('Calibration already stopped.')

    def toggle(self,_=None):
        if self.active:
            self.notify_all({'subject':'calibration.should_stop'})
        else:
            self.notify_all({'subject':'calibration.should_start'})

    def start(self):
        raise  NotImplementedError()
        self.notify_all({'subject':'calibration.started'})


    def stop(self):
        raise  NotImplementedError()
        self.notify_all({'subject':'calibration.stopped'})
