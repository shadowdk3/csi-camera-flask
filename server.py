import flask
import cv2
from flask import render_template, Response, request
import multiprocessing
import time
from multiprocessing import Manager

queue_from_cam = multiprocessing.Queue()
record_btn_msg = ""
manager = Manager()
is_record = manager.Value('i', 0)
is_stream = manager.Value('i', 0)
is_stream.value = 1

prev_record = None

class csiCamera():
    def __init__(self, queue_from_cam):
        global is_stream

        print(self.gstreamer_pipeline(flip_method=0))

        video_capture = None
        try:
            while True:
                if not is_stream.value:
                    video_capture.release()
                    video_capture = None

                if video_capture is None:
                    is_stream.value = 1
                    video_capture = cv2.VideoCapture(self.gstreamer_pipeline(
                        capture_width=1280, 
                        capture_height=720,
                        flip_method=0), cv2.CAP_GSTREAMER)

                ret_val, frame = video_capture.read()

                if not ret_val:
                    continue

                queue_from_cam.put(frame)
                    
        finally:
            video_capture.release()
            print("killed")

    def gstreamer_pipeline(self, sensor_id=0, capture_width=1920, capture_height=1080,
        display_width=960, display_height=540, framerate=30, flip_method=0,):
        return (
            "nvarguscamerasrc sensor-id=%d ! "
            "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
            "nvvidconv flip-method=%d ! "
            "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! appsink"
            % (
                sensor_id,
                capture_width,
                capture_height,
                framerate,
                flip_method,
                display_width,
                display_height,
            )
        )

def generate():
    out = None
    index = 0

    while True:
        from_queue = queue_from_cam.get()

        # encode the frame in JPEG format
        flag, encodedImage = cv2.imencode(".jpg", from_queue)

        # ensure the frame was successfully encoded
        if not flag:
            continue

        if is_record.value:
            if out is None:
                out = 1
                name = 'output/output_' + str(index) + '.mp4'
                print("record name:", name)
                fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                out = cv2.VideoWriter(name, fourcc, 30.0, (from_queue.shape[1],from_queue.shape[0]))
            out.write(from_queue)
        else:
            if out is not None:
                out.release()
                out = None
                index += 1
                
        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

def updateRecordBtnMsg():
    global record_btn_msg

    if is_record.value:
        record_btn_msg = "Stop Recording"
    else:
        record_btn_msg = "Start Recording"

app = flask.Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_record
    global prev_record
    global is_stream

    updateRecordBtnMsg()
    print("open web:", record_btn_msg, "is record:", is_record.value)
    
    if request.method == "POST":
        if request.form.getlist('name'):
            element_name = request.form['name']

            if element_name == "record_btn":
                is_record.value = not is_record.value
                if prev_record and is_record.value == False:
                    is_stream.value = 0

                updateRecordBtnMsg()
                prev_record = is_record.value
                return {'record_btn_msg': record_btn_msg}
	
    # return the rendered template
    return render_template("index.html", record_btn_msg = record_btn_msg)

@app.route("/video_feed")
def video_feed():
	# return the response generated along with the specific media
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    cam_process = multiprocessing.Process(target=csiCamera, args=(queue_from_cam,))
    cam_process.start()

    while queue_from_cam.empty():
        pass

    app.run(host='0.0.0.0', port=8080, debug=False)