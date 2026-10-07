"""One OCR job, change history, cloud boundaries and region resource teardown."""
import threading
import time

from PySide6.QtCore import QObject, Signal, QRect, QEvent, QCoreApplication
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtWidgets import QApplication

from frontengine.utils.screen_text.live_ocr import RegionSource, LiveOcrSession, make_live_reader
from frontengine.utils.screen_text.screen_text_service import ScreenTextResult
from frontengine.utils.screen_text.local_ocr import OcrResult
from frontengine.show.pinned.live_ocr_widget import LiveOcrWidget


def image():
    result=QImage(50,50,QImage.Format.Format_RGB32)
    result.fill(QColor('white'))
    return result


def wait(predicate):
    deadline=time.monotonic()+5
    while not predicate() and time.monotonic()<deadline:
        QApplication.processEvents()
        threading.Event().wait(.005)
    assert predicate()


class Source(QObject):
    frame=Signal(QImage)
    failed=Signal(str)
    def __init__(self):
        super().__init__()
        self.starts,self.stops=0,0
    def start(self,_region):
        self.starts+=1
        self.frame.emit(image())
    def stop(self):
        self.stops+=1


def window(reader,source=None):
    widget=LiveOcrWidget(QRect(0,0,50,50),reader,source=source or Source())
    widget.move(300,200)
    widget.show()
    QApplication.processEvents()
    return widget


def cleanup(widget):
    widget.close()
    if widget.session.thread:
        widget.session.thread.join(5)
    QCoreApplication.sendPostedEvents(widget,QEvent.Type.DeferredDelete)


def test_local_only_reader_never_calls_cloud_even_when_globally_consented():
    class Backend:
        def recognize(self,_data):
            return OcrResult('success','','Local')
    calls=[]
    service=type('Service',(),{'local_backend':Backend(), 'read_result':lambda self,data:calls.append(data)})()
    reader=make_live_reader(service)
    assert reader(b'fixture',False).text=='' and calls==[]
    reader(b'fixture',True)
    assert calls==[b'fixture']


def test_changes_are_unique_and_history_copy_is_explicit():
    current={'text':'one'}
    widget=window(lambda _data,_cloud:ScreenTextResult('success',current['text'],'Injected'))
    try:
        for text in ('one','one','two','one'):
            current['text']=text
            widget.refresh()
            wait(lambda:not widget.busy)
        assert [entry['text'] for entry in widget.history]==['one','two']
        widget.history_box.setCurrentIndex(1)
        clipboard=type('Clipboard',(),{'setText':lambda self,text:setattr(self,'text',text)})()
        widget.copy_text(clipboard=clipboard)
        assert clipboard.text=='two' and widget.current_text=='one'
        for number in range(25):
            widget._completed(ScreenTextResult('success',str(number),'Injected'))
        assert len(widget.history)==20
    finally:
        cleanup(widget)


def test_blocked_ocr_skips_requests_and_close_ignores_late_results():
    entered,release=threading.Event(),threading.Event()
    source=Source()
    def reader(_data,_cloud):
        entered.set()
        assert release.wait(5)
        return ScreenTextResult('success','late','Injected')
    widget=window(reader,source)
    try:
        widget.refresh()
        assert entered.wait(5)
        for _index in range(20):
            widget.refresh()
        assert source.starts==1
        widget.automatic.setChecked(True)
        assert widget.timer.isActive() and widget.interval.minimum()==5
        widget.close()
        release.set()
        widget.session.thread.join(5)
        assert widget.closed and not widget.timer.isActive() and not widget.session.timer.isActive()
        assert widget.session.result is None and widget.history==[] and source.stops>0
    finally:
        release.set()
        cleanup(widget)


def test_hidden_region_does_not_capture_and_cloud_consent_requires_explicit_review():
    calls=[]
    source=Source()
    def reader(_data,cloud):
        calls.append(cloud)
        return ScreenTextResult('unavailable',error='Permission required',consent_required='image')
    widget=window(reader,source)
    requested=[]
    widget.consent_requested.connect(requested.append)
    try:
        widget.refresh()
        wait(lambda:not widget.busy)
        assert calls==[False] and not widget.consent_button.isEnabled() and requested==[]
        widget.cloud.setChecked(True)
        widget.refresh()
        wait(lambda:not widget.busy)
        assert calls==[False,True] and widget.consent_button.isEnabled() and requested==[]
        widget.consent_button.click()
        assert requested==['image']
        widget.automatic.setChecked(True)
        widget.hide()
        assert not widget.timer.isActive()
        widget.refresh()
        assert source.starts==2
    finally:
        cleanup(widget)


def test_overlapping_float_is_rejected_before_capture():
    source=Source()
    widget=window(lambda _data,_cloud:ScreenTextResult('success','text'),source)
    try:
        widget.region=QRect(widget.frameGeometry())
        widget.refresh()
        assert source.starts==0 and not widget.busy and widget.status.text()
    finally:
        cleanup(widget)


def test_qt_source_uses_screen_local_coordinates_and_rejects_cross_screen():
    class Screen:
        def geometry(self):
            return QRect(1280,0,1280,1024)
        def grabWindow(self,*args):
            calls.append(args)
            return QPixmap.fromImage(image())
    calls=[]
    source=RegionSource(screen_provider=lambda _point:Screen())
    frames,failures=[],[]
    source.frame.connect(frames.append)
    source.failed.connect(failures.append)
    source.start(QRect(1500,100,50,50))
    assert calls==[(0,220,100,50,50)] and len(frames)==1
    source.start(QRect(1270,100,50,50))
    assert len(calls)==1 and failures
    source.stop()


def test_native_source_stops_after_one_frame_and_times_out():
    class Native(QObject):
        failed=Signal(str)
        def __init__(self,parent):
            super().__init__(parent)
            self.stops,self.empty=0,False
        def start(self,_rect):
            return True
        def latest_frame(self):
            return None if self.empty else QPixmap.fromImage(image())
        def stop(self):
            self.stops+=1
    source=RegionSource(native_factory=Native)
    frames,failures=[],[]
    source.frame.connect(frames.append)
    source.failed.connect(failures.append)
    source.start(QRect(0,0,50,50))
    source._poll()
    assert len(frames)==1 and not source.timer.isActive() and source.native.stops>0
    source.native.empty=True
    source.start(QRect(0,0,50,50))
    source.polls=166
    source._poll()
    assert failures and not source.timer.isActive()
    source.stop()


def test_session_invalid_or_excessive_text_returns_bounded_error():
    session=LiveOcrSession(lambda _data,_cloud:ScreenTextResult('success','x'*20001))
    results=[]
    session.completed.connect(results.append)
    try:
        assert session.submit(image())
        assert not session.submit(image())
        wait(lambda:bool(results))
        assert results[0].status=='error' and session.busy is False
    finally:
        session.close()
        session.thread.join(5)
