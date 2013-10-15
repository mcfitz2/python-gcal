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
#        cached_events = self.event_cache.get((day.year, day.month, day.day), None)
#        if cached_events:
#            return cached_events
#        else:
        ret = []
        for c in self.calendars["items"]:
            events = self.service.events().list(
                calendarId=c["id"], 
                singleEvents=True, 
                maxResults=1000, 
                orderBy='startTime',
                #timeMin=day.strftime('%Y-%m-%dT00:00:00-05:00'), 
                timeMin=timeMin.isoformat(), 
                #timeMax=(day+datetime.timedelta(days=1)).strftime('%Y-%m-%dT00:00:00-05:00'),
                timeMax=timeMax.isoformat(),
                ).execute()
            ret.extend(filter(lambda event: not event.get("allDay", False), map(self.__parse_dates, events["items"])))
 
            #self.event_cache[(day.year, day.month, day.day)] = ret
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
#        start = dateutil.parser.parse(event["start"].get("date", False) or event["start"].get("dateTime"))
        start = event["start"].get("date", False) or event["start"].get("dateTime")
#        end = dateutil.parser.parse(event["end"].get("date", False) or event["end"].get("dateTime"))
        end = event["end"].get("date", False) or event["end"].get("dateTime")
        events = self.get_events(start, end)
        for e in events:
            e_start = e["start"].get("date", False) or e["start"].get("dateTime")
            e_end = e["end"].get("date", False) or e["end"].get("dateTime")
            if isinstance(e_start, str):
                e_start = dateutil.parser.parse(e_start)
            if isinstance(e_end, str):
                e_end = dateutil.parser.parse(e_end)

            print e["summary"], "==", event["summary"]
            if e["summary"] == event["summary"] and e_start == start and e_end == end:
                return True
        return False


if __name__ == "__main__":
    g = GCal(client_id='800395315239-r1mcb8eebtjnkkf03udpdrnff6fgt5sn.apps.googleusercontent.com',
             client_secret='b2aRVDOypDeSWTG0UExrWwSb',
             scope='https://www.googleapis.com/auth/calendar',
             user_agent='Sub Fetcher/0.01')
    g.exists({"summary":"TCC LH-026", "start":{"dateTime":pytz.timezone("US/Eastern").localize(datetime.datetime(2013, 10, 17, 16, 0, 0))}, "end":{"dateTime":pytz.timezone("US/Eastern").localize(datetime.datetime(2013, 10, 17, 20, 0, 0))}}, calendars=[{"id":"jknc6c60le98j6vl10kbhfo1p8@group.calendar.google.com"}])
