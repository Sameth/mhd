import string
import functools
from fileinput import FileInput
from time import strftime, localtime
from queue import PriorityQueue
import re

import cherrypy

#Scoring constants
OPTIMAL_TRANSFER = 5    #Lowest transfer time with no penalty
c1 = 1                  #Weight of elapsed time
c2 = 1                  #Weight of transfer count
c3 = 1                  #Weight of short transfer time penalty
e2 = 1.5                #Exponent of transfer count
e3 = 2                  #Exponent of shortest transfer time
to_print = 5

def basepage(time, message, connections):
    return   '''<html>
                    <head></head>
                    <body>
                    <p> ''' + message + '''</p>
                    <form method="get" action="index">
                        <input type="text" value="" name="orig">
                        <input type="text" value="" name="dest">
                        <input type="text" value="''' + time + '''" name="time">
                        <button type="submit">Vyhladaj spojenie</button>
                    </form>
                    ''' + connections + '''
                    </body>
                </html>'''

all_stops = []
unique_stops = []

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

#Class describing whole journey.
class Journey:
    def __init__(self, lines = []):
        self.lines = lines

    def add(self, orig, origtime, dest, desttime, line):
        self.lines.append((orig, origtime, dest, desttime, line))

    def __str__(self):
        pass

#TODO: pridat presunutie sa na dalsiu minutu z daneho stavu!
#The actual code that does something, Dijkstra algorithm.
def find(orig, dest, time, day = 0):
    try:
        result = []
        bestscore = [[1000000000000000000 for i in range(3600)] for j in range(len(unique_stops) + 4)]
        printed = 0;
        ends = PriorityQueue()
        ends.put((0, orig, dest, time, Journey(), 0, 0, OPTIMAL_TRANSFER))
        while (not (ends.empty)) and printed < to_print:
            my = ends.get()
            for linenum in stopXtime_lines [my[1]][day][time]:
                startindex = connections[linenum].index(unique_stops[my[1]]);
                for i in range(startindex, len(connections[linenum].stops)):
                    for j in range(OPTIMAL_TRANSFER + 1):
                        difftime = connections[linenum].travel_time[i] - connections[linenum].travel_time[startindex]
                        nexttime = my[5] + difftime
                        nexttransfers = my[6] + 1
                        nextshortest = min(my[7], j)
                        price = score(nexttime, nexttransfers, nextshortest) #Tu dalej sa to cele pokazi!
                        if (price < bestscore [unique_stops.index(connections[linenum].stops[i])][(my[3] + difftime)%3600]):
                            if (unique_stops[dest] == connections [linenum].stops[i]):
                                result.append(my[4])
                            else :
                                bestscore [unique_stops.index(connections[linenum].stops[i])][(my[3] + difftime)% 3600] = price
                                ends.put((price, unique_stops.index(connections[linenum].stops[i]), des, time + difftime,
                                Journey(lines = my[4].lines).add(unique_stops[orig], my[3], connections[linenum].stops[i], my[3] + difftime, connections[linenum].line), nexttime,
                                nexttransfers, nextshortest))
    except Exception as e:
        print(e)

#"Web server"
class JourneyPlanner(object):
    @cherrypy.expose
    def index(self, orig='!', dest='', time=strftime("%H:%M", localtime())):
        if (orig == '!') or orig == dest:
            return basepage(time, '', '')

        else:
            #try:
                orig = orig.replace(u'\xa0', u' ')
                dest = dest.replace(u'\xa0', u' ')
                help1 = re.findall(r'\d+', time);
                time_minutes = int(help1[0])*60 + int(help1[1])
                if (time_minutes >= 3600):
                    return basepage(time, "Incorrect time", '')

                find(unique_stops.index(orig), unique_stops.index(dest), help1)
            #except:
                return basepage(time, "Aaaa!", '')


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
        stops = [origin_stop]
        travel_times = [0]
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
        mystops = conn.stops
        mytimes = conn.travel_times
        for i in range(len(mystops)):
            for j in range (3):
                for k in range(3600):
                    if (conn.departures[j][k]):
                        stopXtime_lines[unique_stops.index(mystops[i])][j][(k + mytimes[i])%3600].append(num)

    cherrypy.quickstart(JourneyPlanner())
