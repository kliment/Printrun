#!/usr/bin/env python
from serial import Serial
from threading import Thread
import time
import sys

class printcore():
    def __init__(self,port=None,baud=None):
        """Initializes a printcore instance. Pass the port and baud rate to connect immediately
        """
        self.baud=None
        self.port=None
        self.printer=None #Serial instance connected to the printer, None when disconnected
        self.clear=0 #clear to send, enabled after responses
        self.online=False #The printer has responded to the initial command and is active
        self.printing=False #is a print currently running, true if printing, false if paused
        self.mainqueue=[] 
        self.priqueue=[]
        self.queueindex=0
        self.lineno=0
        self.resendfrom=-1
        self.paused=False
        self.sentlines={}
        self.log=[]
        self.sent=[]
        self.tempcb=None#impl (wholeline)
        self.recvcb=None#impl (wholeline)
        self.sendcb=None#impl (wholeline)
        self.errorcb=None#impl (wholeline)
        self.startcb=None#impl ()
        self.endcb=None#impl ()
        self.onlinecb=None#impl ()
        self.loud=False#emit sent and received lines to terminal
        if port is not None and baud is not None:
            #print port, baud
            self.connect(port, baud)
            #print "connected\n"
        
        
    def disconnect(self):
        """Disconnects from printer and pauses the print
        """
        if(self.printer):
            self.printer.close()
        self.printer=None
        self.online=False
        self.printing=False
        
    def connect(self,port=None,baud=None):
        """Set port and baudrate if given, then connect to printer
        """
        if(self.printer):
            self.disconnect()
        if port is not None:
            self.port=port
        if baud is not None:
            self.baud=baud
        if self.port is not None and self.baud is not None:
            self.printer=Serial(self.port,self.baud,timeout=5)
            Thread(target=self._listen).start()
            
    def reset(self):
        """Reset the printer
        """
        if(self.printer):
            self.printer.setDTR(1)
            self.printer.setDTR(0)
            
            
    def _listen(self):
        """This function acts on messages from the firmware
        """
        self.clear=True
        time.sleep(0.5)
        self.send_now("M105")
        while(True):
            if(not self.printer or not self.printer.isOpen):
                break
            line=self.printer.readline()
            if(len(line)>1):
                self.log+=[line]
                if self.recvcb is not None:
                    try:
                        self.recvcb(line)
                    except:
                        pass
                if self.loud:
                    print "RECV: ",line.rstrip()
            if(line.startswith('DEBUG_')):
                continue
            if(line.startswith('start') or line.startswith('ok')):
                self.clear=True
            if(line.startswith('start') or line.startswith('ok') or "T:" in line):
                if (not self.online or line.startswith('start')) and self.onlinecb is not None:
                    try:
                        self.onlinecb()
                    except:
                        pass
                self.online=True
                if(line.startswith('ok')):
                    #self.resendfrom=-1
                    #put temp handling here
                    if "T:" in line and self.tempcb is not None:
                        try:
                            self.tempcb(line)
                        except:
                            pass
                    #callback for temp, status, whatever
            elif(line.startswith('Error')):
                if self.errorcb is not None:
                    try:
                        self.errorcb(line)
                    except:
                        pass
                #callback for errors
                pass
            if "resend" in line.lower() or "rs" in line:
                try:
                    toresend=int(line.replace("N:"," ").replace("N"," ").replace(":"," ").split()[-1])
                except:
                    if "rs" in line:
                        toresend=int(line.split()[1])
                self.resendfrom=toresend
                self.clear=True
        self.clear=True
        #callback for disconnect
        
    def _checksum(self,command):
        return reduce(lambda x,y:x^y, map(ord,command))
        
    def startprint(self,data):
        """Start a print, data is an array of gcode commands.
        returns True on success, False if already printing.
        The print queue will be replaced with the contents of the data array, the next line will be set to 0 and the firmware notified.
        Printing will then start in a parallel thread.
        """
        if(self.printing or not self.online or not self.printer):
            return False
        self.printing=True
        self.mainqueue=[]+data
        self.lineno=0
        self.queueindex=0
        self.resendfrom=-1
        self._send("M110",-1, True)
        if len(data)==0:
            return True
        self.clear=False
        Thread(target=self._print).start()
        return True
        
    def pause(self):
        """Pauses the print, saving the current position.
        """
        self.paused=True
        self.printing=False
        time.sleep(1)
        
    def resume(self):
        """Resumes a paused print.
        """
        self.paused=False
        self.printing=True
        Thread(target=self._print).start()
    
    def send(self,command):
        """Adds a command to the checksummed main command queue if printing, or sends the command immediately if not printing
        """
        
        if(self.printing):
            self.mainqueue+=[command]
        else:
            while not self.clear:
                time.sleep(0.001)
            self._send(command,self.lineno,True)
            self.lineno+=1
        
    
    def send_now(self,command):
        """Sends a command to the printer ahead of the command queue, without a checksum
        """
        if(self.printing):
            self.priqueue+=[command]
        else:
            while not self.clear:
                time.sleep(0.001)
            self._send(command)
        #callback for command sent
        
    def _print(self):
        #callback for printing started
        if self.startcb is not None:
            try:
                self.startcb()
            except:
                pass
        while(self.printing and self.printer and self.online):
            self._sendnext()
        if self.endcb is not None:
            try:
                self.endcb()
            except:
                pass
        #callback for printing done
        
    def _sendnext(self):
        if(not self.printer):
            return
        while not self.clear:
            time.sleep(0.001)
        self.clear=False
        if not (self.printing and self.printer and self.online):
            self.clear=True
            return
        if(self.resendfrom<self.lineno and self.resendfrom>-1):
            self._send(self.sentlines[self.resendfrom],self.resendfrom,False)
            self.resendfrom+=1
            return
        self.resendfrom=-1
        for i in self.priqueue[:]:
            self._send(i)
            del(self.priqueue[0])
            return
        if(self.printing and self.queueindex<len(self.mainqueue)):
            tline=self.mainqueue[self.queueindex]
            tline=tline.split(";")[0]
            if(len(tline)>0):
                self._send(tline,self.lineno,True)
                self.lineno+=1
            else:
                self.clear=True
            self.queueindex+=1
        else:
            self.printing=False
            self.clear=True
            if(not self.paused):
                self.queueindex=0
                self.lineno=0
                self._send("M110",-1, True)
            
    def _send(self, command, lineno=0, calcchecksum=False):
        if(calcchecksum):
            prefix="N"+str(lineno)+" "+command
            command=prefix+"*"+str(self._checksum(prefix))
            if("M110" not in command):
                self.sentlines[lineno]=command
        if(self.printer):
            self.sent+=[command]
            if self.loud:
                print "SENT: ",command
            if self.sendcb is not None:
                try:
                    self.sendcb(command)
                except:
                    pass
            self.printer.write(str(command+"\n"))

if __name__ == '__main__':
    #print "Usage: python printcore.py filename.gcode"
    filename="../prusamendel/sellsx_export.gcode"
    if len(sys.argv)>1:
        filename=sys.argv[1]
        print "Printing: "+filename
    else:
        print "Usage: python printcore.py filename.gcode"
        #sys.exit(2)
    p=printcore('/dev/ttyUSB0',115200)
    p.loud=True
    statusreport=False
    time.sleep(2)
    testdata=[i.replace("\n","") for i in open(filename)]
    p.startprint(testdata)
    #time.sleep(1)
    #p.pause()
    #print "pause"
    #time.sleep(5)
    #p.resume()
    try:
        if statusreport:
            p.loud=False
            sys.stdout.write("Progress: 00.0%")
            sys.stdout.flush()
        while(p.printing):
            time.sleep(1)
            if statusreport:
                sys.stdout.write("\b\b\b\b%02.1f%%" % (100*float(p.queueindex)/len(p.mainqueue),) )
                sys.stdout.flush()
    except:
        p.disconnect()
