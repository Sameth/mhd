import string
from time import strftime, localtime

import cherrypy

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
            return 'Not implemented yet!'

if __name__ == '__main__':
    cherrypy.quickstart(JourneyPlanner())
