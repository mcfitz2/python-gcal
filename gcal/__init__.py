import gflags
import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow, AccessTokenCredentials
from oauth2client.tools import run
import dateutil.parser
import pytz
import datetime
import time
import logging
logger = logging.getLogger('')
logger.setLevel(logging.ERROR)
class GCal(object):
    def __init__(self, client_id=None, client_secret=None, scope=None, user_agent=None):
        FLAGS = gflags.FLAGS
        FLOW = OAuth2WebServerFlow(client_id,client_secret,scope,user_agent)
        FLAGS.auth_local_webserver = False
        storage = Storage('credentials.dat')
        credentials = storage.get()
        if credentials is None or credentials.invalid == True:
            credentials = run(FLOW, storage)
        http = httplib2.Http()
        http = credentials.authorize(http)
        self.service = build(serviceName='calendar', version='v3', http=http)
        self.calendars = None 
        self.api_calls = 0
        self.cache = []
    def __parse_dates(self, event):
        for key in ["start", "end"]:
            if event[key].get("date", False):
                event["allDay"] = True
                event[key]["date"] = dateutil.parser.parse(event[key]["date"])
                continue
            elif event[key].get("dateTime", False):
                event[key]["dateTime"] = dateutil.parser.parse(event[key]["dateTime"]).astimezone(pytz.UTC)
                continue
        return event
    def get_events(self, timeMin, timeMax, calendars=None):
        ret = []
        if not self.calendars:
            self.calendars = self.service.calendarList().list().execute()    
        cals = [{"id":cal} for cal in calendars] if calendars else self.calendars["items"]
        for c in  cals:
            def add_cal_id(event):
                event["calendarId"] = c["id"]
                return event

            req = self.service.events().list(
                calendarId=c["id"], 
                singleEvents=True, 
                maxResults=1000, 
                orderBy='startTime',
                timeMin=timeMin.isoformat("T")+"Z", 
                timeMax=timeMax.isoformat("T")+"Z",
                )
     #       print dir(req)
            events = req.execute()
            ret.extend(map(add_cal_id, filter(lambda event: not event.get("allDay", False), map(self.__parse_dates, events["items"]))))
            self.api_calls += 1
        return ret
    def busy(self, start, stop, calendars=None):
        
        if not calendars:
            if not self.calendars:
                self.calendars = self.service.calendarList().list().execute()    
                self.api_calls += 1
            calendars = [{"id":cal["id"]} for cal in self.calendars["items"]]
        else:
            calendars = [{"id":cal} for cal in calendars]
        fb = self.service.freebusy().query(body={"timeMin":start.isoformat(), 
                                               "timeMax":stop.isoformat(), 
                                               "items":calendars,
                                               "groupExpansionMax":10,
                                               "calendarExpansionMax":10}
                                         ).execute()
        self.api_calls += 1
        return any(map(lambda x: len(x["busy"]) > 0, fb["calendars"].itervalues()))

    def exists(self, event, calendars=None):        
        start = event["start"].get("date", False) or event["start"].get("dateTime")
        end = event["end"].get("date", False) or event["end"].get("dateTime")
        events = self.get_events(start, end, calendars=calendars)
        ret = []
        for e in events:
            e_start = e["start"].get("date", False) or e["start"].get("dateTime")
            e_end = e["end"].get("date", False) or e["end"].get("dateTime")
            if isinstance(e_start, str):
                e_start = dateutil.parser.parse(e_start)
            if isinstance(e_end, str):
                e_end = dateutil.parser.parse(e_end)
            if e["summary"] == event["summary"] and e_start == start and e_end == end:
                ret.append(e)
        return (True, ret) if len(ret) > 0 else (False, None)
    def add_event(self, calendarId, name, start, end, location=""):
        self.api_calls += 1
        return self.service.events().insert(calendarId=calendarId, body={"start":{"dateTime":start.isoformat()}, "end":{"dateTime":end.isoformat()}, "location":location, "summary":name}).execute()
    def delete_event(self, calendarId, eventId):
        self.api_calls += 1
        return self.service.events().delete(calendarId=calendarId, eventId=eventId).execute()
    
class GoogleEvent(dict):
    def __init__(self, event_dict):
        dict.__init__(self, event_dict)
        start = event_dict["start"].get("date", False) or event_dict["start"].get("dateTime")
        end = event_dict["end"].get("date", False) or event_dict["end"].get("dateTime")
        if isinstance(start, str):
            start = dateutil.parser.parse(start)
        if isinstance(end, str):
            end = dateutil.parser.parse(end)
        name = event_dict["summary"]
        self.name = name
        self.start = start
        self.end = end
    def __repr__(self):
        event = self.toEastern()
        return "%s - %s from %s to %s" % (event.name, event.start.strftime("%a, %b %d %Y"), event.start.strftime("%I:%M%p"), event.end.strftime("%I:%M%p"))
    def toEastern(self):
        return StandardEvent(self.name, self.start.astimezone(pytz.timezone("US/Eastern")), self.end.astimezone(pytz.timezone("US/Eastern")))

