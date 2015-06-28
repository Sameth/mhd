import string
import functools
from fileinput import FileInput
from time import strftime, localtime

import cherrypy

all_stops = []
day_regime = {'Denne':[0,1,2], 'Pracovné dni':[0,1], 'Voľné dni':[2], 'Pracovné dni (školský rok)':[0], 'Pracovné dni (školské prázdniny)':[1]}
connections = []

class Connection:
    def __init__(self, line, begin, stops, travel_times, departures):
        self.line = line
        self.begin = begin
        self.stops = stops
        self.travel_times = travel_times
        self.departures = departures

class JourneyPlanner(object):
    @cherrypy.expose
    def index(self, orig='!', dest='', time=strftime("%H:%M", localtime())):
        if (orig == '!'):
            return '''<html>
                      <head></head>
                      <body>
                        <form method="get" action="index">
                          <input type="text" value="" name="orig">
                          <input type="text" value="" name="dest">
                          <input type="text" value="''' + time + '''" name="time">
                          <button type="submit">Vyhladaj spojenie</button>
                        </form>
                      </body>
                    </html>'''
        else:
#            re.findall(r'\d+', 'hello 42 I\'m a 32 string 30');
            pass #aaa!


def numberize(x):
    try:
        return [int(x)]
    except:
        return []

def myreadline(f):
    line = f.readline()
    line = line.replace(u'\xa0', u' ')
    return line

def read_data():
    f = FileInput(files=('../data.txt'))
    current_line = myreadline(f)
    while (current_line != ''):
        origin_stop = myreadline(f)[:-1]
        all_stops.append(origin_stop)
        stops = []
        travel_times = []
        current_time = myreadline(f)
        while (current_time != '\n'):
            travel_times.append(int(current_time[:-1]))
            stops.append(myreadline(f)[:-1])
            all_stops.append(stops[-1])
            current_time = myreadline(f)

        tables = int(myreadline(f)[:-1])
        departures = [[False]*3600]*3
        for i in range(tables):
            mode = day_regime[myreadline(f)[:-1]]
            hours = int(myreadline(f)[:-1])
            for j in range(hours):
                numbers = myreadline(f).split()
                for k in functools.reduce(lambda x, y: x+numberize(y),numbers[1:], []):
                    for l in mode:
                        departures [l] [int(numbers[0])] = True

        connections.append(Connection(current_line[:-1], origin_stop, stops, travel_times, departures))
        current_line = myreadline(f)

if __name__ == '__main__':
    read_data()
    all_stops.sort()
    unique_stops = [all_stops[0]]
    for stop in all_stops:
        if (stop != unique_stops[-1]):
            unique_stops.append(stop)

    print(unique_stops)
    cherrypy.quickstart(JourneyPlanner())
