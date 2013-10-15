import gflags
import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
import dateutil.parser
import pytz
import datetime
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
        self.calendars = self.service.calendarList().list().execute()    
        self.event_cache = {}
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
    def get_events(self, timeMin, timeMax):
        ret = []
        for c in self.calendars["items"]:
            events = self.service.events().list(
                calendarId=c["id"], 
                singleEvents=True, 
                maxResults=1000, 
                orderBy='startTime',
                timeMin=timeMin.isoformat(), 
                timeMax=timeMax.isoformat(),
                ).execute()
            ret.extend(filter(lambda event: not event.get("allDay", False), map(self.__parse_dates, events["items"])))
 
        return ret
    def busy(self, start, stop, calendars=None):
        if not calendars:
            calendars = [{"id":cal["id"]} for cal in self.calendars["items"]]
        fb = self.service.freebusy().query(body={"timeMin":start.isoformat(), 
                                               "timeMax":stop.isoformat(), 
                                               "items":calendars,
                                               "groupExpansionMax":10,
                                               "calendarExpansionMax":10}
                                         ).execute()
        print fb
        return any(map(lambda x: len(x["busy"]) > 0, fb["calendars"].itervalues()))

    def exists(self, event, calendars=None):
        start = event["start"].get("date", False) or event["start"].get("dateTime")
        end = event["end"].get("date", False) or event["end"].get("dateTime")
        events = self.get_events(start, end)
        for e in events:
            e_start = e["start"].get("date", False) or e["start"].get("dateTime")
            e_end = e["end"].get("date", False) or e["end"].get("dateTime")
            if isinstance(e_start, str):
                e_start = dateutil.parser.parse(e_start)
            if isinstance(e_end, str):
                e_end = dateutil.parser.parse(e_end)

#            print e["summary"], "==", event["summary"]
#            print e_start, "==", start
#            print e_end, "==", end
#            print "-"*40    
            if e["summary"] == event["summary"] and e_start == start and e_end == end:
                return True
        return False
    def add_event(self, calendarId, name, start, end, location=""):
        return self.service.events().insert(calendarId=calendarId, body={"start":{"dateTime":start.isoformat()}, "end":{"dateTime":end.isoformat()}, "location":location, "summary":name}).execute()
    
