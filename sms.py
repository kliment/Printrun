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
    
    def __init__(self, p_number, carrier):
        """
        p_number can be an int or a string (must be 10 digits with area code)
        carrier parameter needs to be a string from the list:
            [Alltel, ATT, Rogers, Sprint, tMobile, Tellus, Verizon]
        """
        CARRIERS = {"Alltel":"alltelmessage.com", "ATT":"mobile.mycingular.com",
                "Rogers":"pcs.rogers.com", "Sprint":"messaging.sprintpcs.com",
                "tMobile":"t-mobile.net", "Telus":"msg.telus.com",
                "Verizon":"vtext.com"}
        if (type(p_number) == type(0)): ## is phone number and integer?
            p_number = str(p_number)    ## if so, convert to string
        self.address = p_number+'@'+CARRIERS[carrier]
    
class SMSSettings:
    def _carrier_list(self): return ["Alltel", "ATT", "Rogers", "Sprint", "tMobile", "Telus", "Verizon"]
    def __init__(self):
        # defaults here.
        # the initial value determines the type
        self.gmail_username = "GMAIL_USERNAME@gmail.com"
        self.gmail_password = "GMAIL_PASSWORD"
        self.phonenumber = "PHONENUMBER"
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
        print "Sending SMS Message to " +self.sms_settings.phonenumber+"@"+self.smscmb.GetValue()      
        sender = Sender(self.sms_settings.gmail_username, self.sms_settings.gmail_password)  
        txtM = TextMessage(subject, message)
        receiver = Receiver(self.sms_settings.phonenumber, self.smscmb.GetValue())
        sender.sendMessage(receiver, txtM)