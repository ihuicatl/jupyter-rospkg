import os
import tornado

from notebook.base.handlers import IPythonHandler

import rospkg


class Pkgs(IPythonHandler):
    rospack = rospkg.RosPack()

    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        cls = self.__class__

        if not args:
            self.write("Error - no argument supplied")
            self.finish()
            return
        
        print("[PKGS] get:", args[0])
        
        argslist = args[0].split('/')
        
        package = argslist[0]
        file = '/'.join(argslist[1:])
        path = ""

        try :
            path = cls.rospack.get_path(package)
        except rospkg.ResourceNotFound :
            self.write(f"Package {package} not found")
            self.finish()
            return

        try:
            with open(os.path.join(path, file), 'rb') as f:
                data = f.read()
                self.write(data)
        except:
            self.write(f"Error opening file {file}")

        self.finish()
