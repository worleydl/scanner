from time import time;
import numpy
import pyaudio
import socket
import subprocess

CHUNK_SIZE = 1500
CUSHION = 5 # Keep channel open for this long after activity detected
PORT_BASE = 15000
THRESHOLD = 5000

class Station:
    def __init__(self, name, url):
        global PORT_BASE

        self.error = False
        self.error_time = 0
        self.name = name
        self.url = url
        self.port = PORT_BASE
        self.stream_active = False

        PORT_BASE += 1

    def stream(self):
        args = '-i {} -b 900k -f wav udp://127.0.0.1:{}'.format(self.url, self.port)

        print('Running ffmpeg with: ', args)
        self.hook = subprocess.Popen(['ffmpeg'] + args.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def prepare(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5.0)
        self.sock.bind(('127.0.0.1', self.port))


    def sample(self):
        return self.buff

    def tick(self):
        global CHUNK_SIZE, CUSHION, THRESHOLD

        if self.error:
            self.stream_active = False

            if time() - self.error_time > 60:
                self.error = False
                print('Resuming {}'.format(self.name))
                self.stream()
                self.prepare()

            return


        # Sometimes streams have errors, restart ffmpeg when that occurs
        if(self.hook.poll() is not None):
            self.error = True
            self.error_time = time()
            return

        try:
            data, addr = self.sock.recvfrom(CHUNK_SIZE)
        except:
            self.error = True
            self.error_time = time()
            self.hook.kill()
            return

        sample = numpy.fromstring(data, dtype=numpy.int16)
        peak = numpy.average(numpy.abs(sample)) * 2
        if peak > THRESHOLD:
            if not self.stream_active:
                print(self.name)

            self.last_activity = time()
            self.stream_active = True
        elif time() - self.last_activity > CUSHION:
            self.stream_active = False

        self.buff = data


stations = []

stations.append(Station('Augusta County Sheriff', 'http://relay.broadcastify.com:80/776430623.mp3'))
stations.append(Station('Staunton PD', 'http://relay.broadcastify.com:80/bw8xcrt5f2pk.mp3'))
stations.append(Station('State Police', 'http://relay.broadcastify.com:80/34238472.mp3'))
#stations.append(Station('Chicago', 'http://relay.broadcastify.com:80/il_chicago_police2.mp3'))

for station in stations:
    station.stream()
    station.prepare()

WIDTH = 2
CHANNELS = 1
RATE = 22050

p = pyaudio.PyAudio()
stream = p.open(format=p.get_format_from_width(WIDTH),
        channels=CHANNELS,
        rate=RATE,
        output=True)

while True:
    for station in stations:
        station.tick()

    for station in stations:
        if(station.stream_active):
            stream.write(station.sample())
            break

p.terminate()
