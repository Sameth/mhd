import string
import functools
from fileinput import FileInput
from time import strftime, localtime
from queue import PriorityQueue
import re
import traceback
import cherrypy

#Scoring constants
OPTIMAL_TRANSFER = 5    #Lowest transfer time with no penalty
c1 = 1                  #Weight of elapsed time
c2 = 1                  #Weight of transfer count
c3 = 1                  #Weight of short transfer time penalty
e2 = 1.5                #Exponent of transfer count
e3 = 2                  #Exponent of shortest transfer time
to_print = 5            #Number of connections to print
daylength = 1440        #Number of minutes in a day

def basepage(time, message, connections):
    return   '''<!DOCTYPE html>
                <html>
                    <head>
                    <style>
                    .t01 tr:nth-child(even) {
                        background-color: #eee;
                    }
                    table#t01 tr:nth-child(odd) {
                        background-color:#fff;
                    }
                    .t01 th{
                        background-color: black;
                        color: white;
                    }
                    </style>
                    </head>
                                                       
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
        return str(self.line)

        

#Class describing whole journey.
class Journey:
    def __init__(self, lines = []):
        self.lines = lines

    def add(self, orig, origtime, dest, desttime, line):
        self.lines.append((orig, origtime, dest, desttime, line))
        return self

    def __str__(self):
        return str(self.lines)

    def __repr__(self):
        return str(self.lines)

    def __lt__(self, other):
        return False

    def __le__(self, other):
        return True

    def __gt__(self, other):
        return False

    def __ge__(self, other):
        return True

    def __eq__(self, other):
        return True

    def formatted(self):
        toreturn = ""
        for tup in self.lines:
            toreturn += """<tr>
                         <td>""" + tup[4] + """
                         <td>""" + tup[0] + ' ' + "%02d:%02d" % ((tup[1] % daylength) // 60, tup[1] % 60) + """</td>
                         <td>""" + tup[2] + ' ' + "%02d:%02d" % ((tup[3] % daylength) // 60, tup[3] % 60) + """</td>
                        </tr>
                        """

        return toreturn

#TODO: pridat presunutie sa na dalsiu minutu z daneho stavu!
#The actual code that does something, Dijkstra algorithm.
def find(orig, dest, time, day = 0):
    try:
        result = []
        bestscore = [[1000000000000000000 for i in range(daylength)] for j in range(len(unique_stops) + 4)]
        printed = 0;
        ends = PriorityQueue()
        ends.put((0, orig, dest, time, Journey(), 0, 0, OPTIMAL_TRANSFER))
        while (not (ends.empty())) and printed < to_print:
#            print("iterujem!")
            my = ends.get()
            #if (my[4] == None):
#            print(my)
#            print(my[1], day, my[3])
            for linenum in stopXtime_lines [my[1]][day][my[3] % daylength]:
#                print(linenum)
                startindex = connections[linenum].stops.index(unique_stops[my[1]]);
                for i in range(startindex + 1, len(connections[linenum].stops)):
                    for j in range(OPTIMAL_TRANSFER + 1):
                        difftime = connections[linenum].travel_times[i] - connections[linenum].travel_times[startindex] + j
                        nexttime = my[5] + difftime
                        nexttransfers = my[6] + 1
                        nextshortest = min(my[7], j)
                        price = score(nexttime, nexttransfers, nextshortest) #Tu dalej sa to cele pokazi!
                        if (price < bestscore [unique_stops.index(connections[linenum].stops[i])][(my[3] + difftime)%daylength]):
                            if (unique_stops[dest] == connections [linenum].stops[i]) and (j == 0):
                                result.append(Journey(lines=list(my[4].lines)).add(unique_stops[my[1]], my[3], connections[linenum].stops[i], my[3] + difftime, connections [linenum].line))
                                printed += 1
                            else :
                                bestscore [unique_stops.index(connections[linenum].stops[i])][(my[3] + difftime)% daylength] = price
                                ends.put((price, unique_stops.index(connections[linenum].stops[i]), dest, my[3] + difftime,
                                Journey(lines = list(my[4].lines)).add(unique_stops[my[1]], my[3], connections[linenum].stops[i], my[3] + difftime, connections[linenum].line), nexttime,
                                nexttransfers, nextshortest))

            if (my[0] + 1 < bestscore [my[1]][(my[3]+1) % daylength]):
                bestscore [my[1]][(my[3] + 1) % daylength] = my[0] + 1;
                ends.put((my[0] + 1, my[1], my[2], my[3] + 1, my[4], my[5], my[6], my[7]))
        return result
    except Exception as e:
        traceback.print_exc()

def generate_output(journeys):
    output = """<table border="1">
    """

    for journey in journeys:
        output += """<tr><td>
                        <table class="t01">
                        """
        output += journey.formatted()
        output += """   </table>
                    </td></tr>
                    """

    output += "</table>"
    return output

#"Web server"
class JourneyPlanner(object):
    @cherrypy.expose
    def index(self, orig='!', dest='', time=strftime("%H:%M", localtime())):
        if (orig == '!') or orig == dest:
            return basepage(time, '', '')

        else:
            try:
                orig = orig.replace(u'\xa0', u' ')
                dest = dest.replace(u'\xa0', u' ')
                help1 = re.findall(r'\d+', time);
                time_minutes = int(help1[0])*60 + int(help1[1])
                if (time_minutes >= daylength):
                    return basepage(time, "Incorrect time", '')

                magic = find(unique_stops.index(orig), unique_stops.index(dest), time_minutes)
                return basepage(time, '', generate_output(magic))
            except:
                return basepage(time, "Incorrect stop (probably)", '')


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
        departures = [[False for i in range(daylength)]for j in range(3)]
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

    stopXtime_lines = [[[[] for i in range(daylength)] for j in range(3) ] for k in range(len(unique_stops) + 4)]

    for num in range(len(connections)):
        conn = connections[num]
        mystops = conn.stops
        mytimes = conn.travel_times
        for i in range(len(mystops)):
            for j in range (3):
                for k in range(daylength):
                    if (conn.departures[j][k]):
                        stopXtime_lines[unique_stops.index(mystops[i])][j][(k + mytimes[i])%daylength].append(num)

    cherrypy.quickstart(JourneyPlanner())
