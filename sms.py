#!/usr/bin/env python
import cmd, printcore, sys 
import glob, os, time
import sys, subprocess 
import math
import libgmail

from math import sqrt

if os.name=="nt":
    try:
        import _winreg
    except:
        pass
READLINE=True
try:
    import readline
    try:
        readline.rl.mode.show_all_if_ambiguous="on" #config pyreadline on windows
    except:
        pass
except:
    READLINE=False #neither readline module is available

class Sender:
    """
    This type acts a system to send messages    
    """
    def __init__(self, uname, psswd):
        # fill these if you will be using the same account often
        self.user_name = uname
        self.password = psswd
        self.ga = libgmail.GmailAccount(self.user_name, self.password)
        self.ga.login()
    def sendMessage(self, receiver, mssg):
        ## had to switch message and body argument for some reason!?
        gMssg = libgmail.GmailComposedMessage(receiver.address, mssg.body, mssg.subject)
        gStub = self.ga.sendMessage(gMssg)
    
class TextMessage:
    """
    Acts as a generic type for a text message
    """
    def __init__(self,_body, _subject, _att = None):
        self.subject = _subject
        self.body = _body
        self.att = _att    
    
class Receiver:
    """
    This type is to represent a reciever of a text message
    """
    
    def __init__(self, p_number, carrier, other):
        """
        p_number can be an int or a string (must be 10 digits with area code)
        carrier parameter needs to be a string from the list:
            [Alltel, ATT, Rogers, Sprint, tMobile, Tellus, Verizon]
        """
        CARRIERS = {"Alltel":"alltelmessage.com", "ATT":"mobile.mycingular.com",
                "Rogers":"pcs.rogers.com", "Sprint":"messaging.sprintpcs.com",
                "tMobile":"t-mobile.net", "Telus":"msg.telus.com",
                "Verizon":"vtext.com", "Other":""}
        if(carrier == "Other"):
            self.address = p_number+'@'+other
        else:
            if (type(p_number) == type(0)): ## is phone number and integer?
                p_number = str(p_number)    ## if so, convert to string
            self.address = p_number+'@'+CARRIERS[carrier]
    
class SMSSettings:
    def _carrier_list(self): return ["Alltel", "ATT", "Rogers", "Sprint", "tMobile", "Telus", "Verizon", "Other"]
    def __init__(self):
        # defaults here.
        # the initial value determines the type
        self.gmail_username = "GMAIL_USERNAME@gmail.com"
        self.gmail_password = "GMAIL_PASSWORD"
        self.phonenumber = "PHONENUMBER"
        self.other_carrier = ""
    def _set(self,key,value):
        try:
            value = getattr(self,"_%s_alias"%key)()[value]
        except KeyError:
            pass
        except AttributeError:
            pass
        try:
            getattr(self,"_%s_validate"%key)(value)
        except AttributeError:
            pass
        setattr(self,key,type(getattr(self,key))(value))
        try:
            getattr(self,"_%s_cb"%key)(key,value)
        except AttributeError:
            pass
        return value
    def _tabcomplete(self,key):
        try:
            return getattr(self,"_%s_list"%key)()
        except AttributeError:
            pass
        try:
            return getattr(self,"_%s_alias"%key)().keys()
        except AttributeError:
            pass
        return []
    def _all_settings(self):
        return dict([(k,getattr(self,k)) for k in self.__dict__.keys() if not k.startswith("_")])

class sms(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.sms_settings = SMSSettings()
    
    def send_sms(self,subject,message):
        """send sms message"""
        if(self.smscmb.GetValue() == "Other"):
            print "Sending SMS Message ("+subject+"::"+message+") to " +self.sms_settings.phonenumber+"@"+self.sms_settings.other_carrier   
        else:  
            print "Sending SMS Message ("+subject+"::"+message+") to " +self.sms_settings.phonenumber+"@"+self.smscmb.GetValue()      
        sender = Sender(self.sms_settings.gmail_username, self.sms_settings.gmail_password)  
        txtM = TextMessage(subject, message)
        receiver = Receiver(self.sms_settings.phonenumber, self.smscmb.GetValue(),self.sms_settings.other_carrier)
        sender.sendMessage(receiver, txtM)
    
    def smsset(self,var,str):
        try:
            t = type(getattr(self.sms_settings,var))
            value = self.sms_settings._set(var,str)
            if not self.processing_rc and not self.processing_args:
                self.save_in_rc("set "+var,"set %s %s" % (var,value))
        except AttributeError:
            print "Unknown SMS variable '%s'" % var
        except ValueError, ve:
            print "Bad value for variable '%s', expecting %s (%s)" % (var,repr(t)[1:-1],ve.args[0])
    
    def do_set(self,argl):
        args = argl.split(None,1)
        if len(args) < 1:
            for k in [kk for kk in dir(self.sms_settings) if not kk.startswith("_")]:
                print "%s = %s" % (k,str(getattr(self.sms_settings,k)))
            return
            value = getattr(self.sms_settings,args[0])
        if len(args) < 2:
            try:
                print "%s = %s" % (args[0],getattr(self.sms_settings,args[0]))
            except AttributeError:
                print "Unknown SMS variable '%s'" % args[0]
            return
        self.set(args[0],args[1])
    
    def help_set(self):
        print "Set variable:   set <variable> <value>"
        print "Show variable:  set <variable>"
        print "'set' without arguments displays all variables"

    def complete_set(self, text, line, begidx, endidx):
        if (len(line.split())==2 and line[-1] != " ") or (len(line.split())==1 and line[-1]==" "):
            return [i for i in dir(self.sms_settings) if not i.startswith("_") and i.startswith(text)]
        elif(len(line.split())==3 or (len(line.split())==2 and line[-1]==" ")):
            return [i for i in self.sms_settings._tabcomplete(line.split()[1]) if i.startswith(text)]
        else:
            return []
    