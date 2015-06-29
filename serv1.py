import string
import functools
from fileinput import FileInput
from time import strftime, localtime

import cherrypy

#Scoring constants
OPTIMAL_TRANSFER = 5    #Lowest transfer time with no penalty
c1 = 1                  #Weight of elapsed time
c2 = 1                  #Weight of transfer count
c3 = 1                  #Weight of short transfer time penalty
e2 = 1.5                #Exponent of transfer count
e3 = 2                  #Exponent of shortest transfer time

all_stops = []

stopXtime_lines = []

#Applicable in Bratislava:
day_regime = {'Denne':[0,1,2], 'Pracovné dni':[0,1], 'Voľné dni':[2], 
                'Pracovné dni (školský rok)':[0], 'Pracovné dni (školské prázdniny)':[1]}
connections = []

#Scoring function
def score(time, transfers, shortest_transfer):
    return c1 * time + c2 * transfers**e2 + c3 * max (OPTIMAL_TRANSFER - shortest_transfer, 0)**e3
    

#A base class for one line with direction.
class Connection:
    def __init__(self, line, begin, stops, travel_times, departures):
        self.line = line
        self.begin = begin
        self.stops = stops
        self.travel_times = travel_times
        self.departures = departures

    def __str__(self):
        return self.line

#"Web server"
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

#Helper function
def numberize(x):
    try:
        return [int(x)]
    except:
        return []

#The source intermixed different kinds of spaces
def myreadline(f):
    line = f.readline()
    line = line.replace(u'\xa0', u' ')
    return line

#Read timetable data from file
def read_data():
    f = FileInput(files=('data.txt'))
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
        departures = [[False for i in range(3600)]for j in range(3)]
        for i in range(tables):
            mode = day_regime[myreadline(f)[:-1]]
            hours = int(myreadline(f)[:-1])
            for j in range(hours):
                numbers = myreadline(f).split()
                for k in functools.reduce(lambda x, y: x+numberize(y),numbers[1:], []):
                    for l in mode:
                        departures [l] [int(numbers[0])*60 + k] = True

        connections.append(Connection(current_line[:-1], origin_stop, stops, travel_times, departures))
        current_line = myreadline(f)

if __name__ == '__main__':
    read_data()
    all_stops.sort()
    unique_stops = [all_stops[0]]
    for stop in all_stops:
        if (stop != unique_stops[-1]):
            unique_stops.append(stop)

    stopXtime_lines = [[[[] for i in range(3600)] for j in range(3) ] for k in range(len(unique_stops) + 4)]

    for num in range(len(connections)):
        conn = connections[num]
        mystops = [conn.begin]+conn.stops
        mytimes = [0]+conn.travel_times
        for i in range(len(mystops)):
            for j in range (3):
                for k in range(3600):
                    if (conn.departures[j][k]):
                        stopXtime_lines[unique_stops.index(mystops[i])][j][(k + mytimes[i])%3600].append(num)

    cherrypy.quickstart(JourneyPlanner())
