from time import time
from typing import List
from queue import Queue
from copy import deepcopy
from threading import Thread, Lock
from os import environ, access, R_OK, scandir
from os.path import normpath, join, isdir, islink, exists


class WorkspaceContext:
    def __init__(self, abs_path, check_devel=True, check_build=True,
                 check_src=True, is_ws=True) -> None:
        self.abs_path = abs_path
        self.ws = is_ws
        self.ns = True
        self.sub_folders_exsists = {
                                    "devel": not check_devel,
                                    "src": not check_src,
                                    "build": not check_build
                                    }

    def is_ws(self):
        self.ws = self.sub_folders_exsists["devel"] and \
                self.sub_folders_exsists["src"] and \
                self.sub_folders_exsists["build"] and self.ns
        return self.ws


def remove_spaces(path: str) -> str:
    """
    Args:
    - path: string

    Returns:
    - path: string without trailing spaces
    """
    return path.strip()


def get_folders(abs_path: str) -> List[str]:
    """
    Args:
    abs_path:str : Absoulte path to the folder

    Returns:
    folder_paths:List[str] : List of folders in current folder whose
                             local path doesn't start with the
                             following characters
                                - src
                                - devel
                                - build
                                - .
    """
    global WORKSPACES, SUB_FOLDERS_TO_CHECK
    folder_paths = []
    if access(abs_path, R_OK) and not (islink(abs_path)
                                       or abs_path in WORKSPACES):
        for local_path in scandir(abs_path):
            if local_path.is_dir(follow_symlinks=False):
                folder_path = local_path.name
                if not folder_path.startswith(('.', *SUB_FOLDERS_TO_CHECK)):
                    possible_folder_path = join(abs_path, folder_path)
                    folder_paths.append(possible_folder_path)
    return folder_paths


def find_workspaces(abs_path: str, protection: Lock = None,
                    workspace_suffix: str = ''):
    """
    Check if the folder has the following sub-paths
        A valid workspace
            - src
            - devel
            - build
    """
    global SUB_FOLDERS_TO_CHECK
    abs_path = normpath(abs_path)

    if access(abs_path, R_OK):

        possible_ws = WorkspaceContext(abs_path)

        if workspace_suffix != '':
            if not possible_ws.abs_path.endswith(workspace_suffix):
                possible_ws.ns = False
                return

        for folder in SUB_FOLDERS_TO_CHECK:
            folder_path = normpath(join(abs_path, folder))
            if exists(folder_path) and isdir(folder_path):
                possible_ws.sub_folders_exsists[folder] = True

        if possible_ws.is_ws():
            with protection:
                global WORKSPACES
                WORKSPACES.update([possible_ws.abs_path])

    else:
        print(f"[WSP] Warn : Not accessible - {abs_path}")


def get_sourced_workspaces(ros_path: str, delim: str = ':') -> List[str]:
    """
    Args:
    - ros_path: str : Absoulte paths to already sourced workspaces.
    - delim: str    : A single character thats the absoulte paths.

    Returns:
    - path_list: List[str] : A list of strings of the absoulte paths with
                             trailing spaces removed.
    """
    path_list = ros_path.split(delim)
    path_list = [remove_spaces(path) for path in path_list if path != '']
    return path_list


def ws_finder(queue, lock):
    while True:
        abs_path = queue.get()
        find_workspaces(abs_path, lock)
        queue.task_done()


def workspace_parser():

    global SEARCH_PATHS, NEXT_PATHS_TO_SEARCH, WORKSPACES, \
            MAX_THREAD_LIMIT, __name__

    threads = []
    lock = Lock()
    total_file_paths = 0

    for t in range(MAX_THREAD_LIMIT):
        thread = Thread(target=ws_finder, args=(SEARCH_PATHS, lock,),
                        name=f"ws_finder_{t}", daemon=True)
        thread.start()
        threads.append(thread)

    start_time = time()
    while NEXT_PATHS_TO_SEARCH != []:
        total_file_paths += len(NEXT_PATHS_TO_SEARCH)
        folders_in_cur_dir = []
        for abs_path in NEXT_PATHS_TO_SEARCH:
            folders_in_cur_dir += get_folders(abs_path)
        [SEARCH_PATHS.put(folder) for folder in NEXT_PATHS_TO_SEARCH]
        NEXT_PATHS_TO_SEARCH = deepcopy(folders_in_cur_dir)
        del folders_in_cur_dir

    SEARCH_PATHS.join()
    end_time = time()

    if __name__ == "__main__":
        print(f"[WSP] Info : Parsed Paths: {total_file_paths}\n\
             No of Workspaces found: {len(WORKSPACES)}\n\
             Processing Time: {end_time-start_time:.2f} secs")

    WORKSPACES = list(WORKSPACES)
    return WORKSPACES


ROS_PACKAGE_PATH = environ.get("ROS_PACKAGE_PATH", default="")
SOURCED_WORKSPACES = get_sourced_workspaces(ROS_PACKAGE_PATH)
SUB_FOLDERS_TO_CHECK = ("devel", "src", "build")
HOME = environ.get("HOME", default="/")

WORKSPACES = set(SOURCED_WORKSPACES)
MAX_THREAD_LIMIT = 10

# starting location - home
SEARCH_PATHS = Queue()
NEXT_PATHS_TO_SEARCH = get_folders(HOME)


if __name__ == "__main__":
    print(f"[WSP] Info : Start Dir - {HOME}")
    print("[WSP] Info : ROS_PACKAGE_PATH=", ':'.join(workspace_parser()),
          sep="")
