from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os, cgi, shutil
import subprocess
import time
import thread
import json
import SimpleHTTPServer
import SocketServer

class BooleanFile():
    def __init__(self, fileName):
        self.booleanFileName = fileName
    
    def createFile(self, text =''):
        if not self.fileExists():
            booleanFile = open(self.booleanFileName, 'w')
            booleanFile.write(text)
            booleanFile.close()
    
    def readFile(self ):
        params = {}
        if self.fileExists():
            booleanFile = open(self.booleanFileName, 'r')
            params = json.load(booleanFile)
            
        return params        
    def fileExists(self):
        return os.path.lexists(self.booleanFileName)
    
    def removeFile(self):
        if os.path.lexists(self.booleanFileName):
            os.remove(self.booleanFileName)
        
    
class MyHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    
    def getPostVars(self):
        if int(self.headers.getheader('content-length')) > 0:
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers.getheader('content-length'))
                postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                postvars = {}
        else:
            postvars = {}
        return postvars
    
    def do_POST(self):
        self.stopFile = BooleanFile('stop')
        self.activeFile = BooleanFile('active')   
        p = self.path.split("?")
        path = p[0][1:].split("/")
        
        postvars = self.getPostVars()
        
        
        if path[-1] == 'stop':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

        
            self.stopFile.createFile()
            self.wfile.write(json.dumps({'status' :'stop sent'} ))
        
        elif path[-1] == 'active':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            if self.activeFile.fileExists():
                params = self.activeFile.readFile()
                if self.stopFile.fileExists():
                    self.wfile.write(json.dumps({'active' :True,'params':params,'message':'stopping on next cycle'} ))
                else:
                    self.wfile.write(json.dumps({'active' :True,'params':params,'message':'active'} ))
            else:
                self.wfile.write( json.dumps({'active' :False,'message':'not active'} ))
        
        elif path[-1] == 'samplePic':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            for i in range(11):
                if os.path.lexists("/dev/video" + str(i)):
                    self.WEBCAM = "/dev/video" + str(i)
                    break
            self.takePicture('.' ,('800','600') )
                
        elif path[-1] == 'start': 
            
            self.stopFile.removeFile()
            for i in range(11):
                if os.path.lexists("/dev/video" + str(i)):
                    self.WEBCAM = "/dev/video" + str(i)
                    break
                
            if postvars.has_key('project'):
                folder = self.server.mediaFolderDefault + '/' + postvars['project'][0] + '/'
                if not os.path.lexists(folder):
                    os.mkdir(folder)
            else:
                folder = self.server.mediaFolderDefault + '/'
            
            if postvars.has_key('imageWidth'):
                imageWidth = postvars['imageWidth'][0]
            else:
                imageWidth = self.server.imageWidthDefault
            
            if postvars.has_key('imageHeight'):
                imageHeight = postvars['imageHeight'][0]
            else:
                imageHeight = self.server.imageHeightDefault
                 
            if postvars.has_key('seconds') & postvars['seconds'][0].isdigit():
                thread.start_new_thread(self.activateCamera , (postvars['seconds'][0], folder, postvars['project'][0], (imageWidth, imageHeight) ) )
                cameraParam = {'seconds': postvars['seconds'][0],'device': self.WEBCAM,'folder': folder}
                jsonResponse = json.dumps( {'status':'camera started','cameraParam': cameraParam} )
            else:
                cameraParam = {'seconds': postvars['seconds'][0],'device': self.WEBCAM,'folder': folder}
                jsonResponse = json.dumps( {'status':'camera not started','cameraParam': cameraParam} )
                
            self.wfile.write(jsonResponse)        
            
 
        return
    
    def takePicture(self, directory , resolution, currtime=None, fileName=None):
        if currtime is None:
            currtime = str(time.strftime("%X"))
        if fileName is None:
            fileName = directory + currtime + ".jpeg"
        resolution = '%sx%s' % (resolution[0] , resolution[1])
        subprocess.call(["streamer", "-c", self.WEBCAM, "-s", resolution, "-o", fileName])
        shutil.copy (fileName, self.server.sampleFile)
        print(fileName)

    def activateCamera(self, seconds, directory ='/tmp/',  project=None, resolution =('800','600'), fileName=None):
        cameraParam = {'seconds': seconds,'device': self.WEBCAM,'folder': directory,'project':project, 'resolution': resolution}
        self.activeFile.createFile( json.dumps(cameraParam) )
        while not self.stopFile.fileExists():
            self.takePicture(directory, resolution, fileName =fileName)
            time.sleep(float(seconds))
            
        print('camera stopped')
        self.stopFile.removeFile()
        self.activeFile.removeFile()
                
    def log_request(self, code=None, size=None):
        print('Request')

    def log_message(self, format, *args):
        print('Message')


class MyHTTPServer(SocketServer.TCPServer):
    """this class is necessary to allow passing custom request handler into
       the RequestHandlerClass"""
    def __init__(self, server_address, RequestHandlerClass):
        self.sampleFile = 'samplePic.jpeg'  
        self.imageWidthDefault = '800'
        self.imageHeightDefault = '600' 
        self.mediaFolderDefault = 'media'
        if not os.path.lexists(self.mediaFolderDefault):
            os.mkdir(self.mediaFolderDefault)
        stopFile = BooleanFile('stop')
        stopFile.removeFile()
        activeFile = BooleanFile('active')
        activeFile.removeFile()
        activeFile = BooleanFile(self.sampleFile)
        activeFile.removeFile()
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass) 
        #HTTPServer.__init__(self, server_address, RequestHandlerClass)   


def checkStreamerIsInstalled():
    if subprocess.call(["which", "streamer"] , stdout=subprocess.PIPE) is not 0:
        print("The program streamer, which pySnap requires to run, has not been detected. Enter in your password to install streamer, or press Control - C to exit the program.")
        if os.path.lexists("streamer.deb"):
            subprocess.call(["sudo", "dpkg", "-i", "streamer.deb"])
        else:
            subprocess.call(["sudo", "apt-get", "install", "-y", "streamer"])


def getMyIP():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com",80))
    my_ip =s.getsockname()[0] 
    s.close()
    return my_ip

if __name__ == "__main__":
    try:
        checkStreamerIsInstalled()
        port = 8800
        server = MyHTTPServer(('', port), MyHandler)
        url = "http://%s:%d" % (getMyIP(), port)
        print('Started http server. go to ' + url) 
        #webbrowser.open(url,new='new')
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()
        
        


