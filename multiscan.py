#!/usr/bin/env python2.7
# -*- encoding: utf8 -*-

import requests
import re
import os
import argparse
import sys
from threading import Thread, Event, Lock
from Queue import Queue
from bs4 import BeautifulSoup


class Multiscanner:
    ENGINE_BING = 'bing'
    ENGINE_ASK = 'ask'
    ENGINE_RAMBLER = 'rambler'
    ENGINE_GOOGLE = 'google'

    def __init__(self, dork_file, output, threads):
        self.dork_file = dork_file
        self.output = output
        self.links = []
        self.ptr_limits = {
            'bing': 411,
            'ask': 20,
            'rambler': 20,
            'google': 20
        }
        self.exclude_itens = 'msn|microsoft|php-brasil|facebook|' \
                             '4shared|bing|imasters|phpbrasil|php.net|yahoo|' \
                             'scrwordtbrasil|under-linux|google|msdn|ask|' \
                             'bing|rambler|youtube'
        self.engines = {
            Multiscanner.ENGINE_BING: {
                'progress_string': '[***Bing***] Quering page {}/{} with dork {}\n',
                'search_string': 'http://www.bing.com/search?q={}&count=50&first={}',
                'page_range': xrange(1, self.ptr_limits['bing'], 10)
            },
            Multiscanner.ENGINE_ASK: {
                'progress_string': '[***Ask***] Quering page {}/{} with dork {}\n',
                'search_string': 'http://www.ask.com/web?q={}&page={}',
                'page_range': xrange(1, self.ptr_limits['ask'])
            },
            Multiscanner.ENGINE_RAMBLER: {
                'progress_string': '[***Rambler***] Quering page {}/{} with dork {}\n',
                'search_string': 'http://nova.rambler.ru/search?query={}&page={}',
                'page_range': xrange(1, self.ptr_limits['rambler'])
            },
		Multiscanner.ENGINE_GOOGLE: {
                'progress_string': '[***GOOGLE***] Quering page {}/{} with dork {}\n',
                'search_string': 'http://www.google.com/search?q={}&page={}',
                'page_range': xrange(1, self.ptr_limits['google'])
            },
        }

        self.threads = threads
        self.q = Queue()
        self.t_stop = Event()
        self.counter = 0
        self.list_size = len(open(self.dork_file).readlines())
        self.lock = Lock()
        self.terminal = sys.stdout

    @staticmethod
    def get_engines():
        """Get current engines"""
        return [
            Multiscanner.ENGINE_BING,
            Multiscanner.ENGINE_ASK,
            Multiscanner.ENGINE_RAMBLER,
            Multiscanner.ENGINE_GOOGLE
        ]

    def get_links(self, word, engine):
        """Fetch links from engnies"""
        self.links = []
        current_engine = self.engines[engine]

        for ptr in current_engine['page_range']:
            with self.lock:
                self.terminal.write(current_engine['progress_string'].format(
                    ptr, self.ptr_limits[engine], word
                ))

            content = requests.get(
                current_engine['search_string'].format(word, str(ptr))
            )

            if content.ok:
                try:
                    soup = BeautifulSoup(content.text, 'html.parser')

                    for link in soup.find_all('a'):
                        link = link.get('href')

                        if 'http' in link and not re.search(
                            self.exclude_itens, link
                        ):

                            if link not in self.links:
                                self.links.append(link)
                                with self.lock:
                                    with open(self.output, 'a+') as fd:
                                        fd.write(link + '\n')
                except Exception:
                    pass

    def search(self, q):
        """Control flow"""
        while not self.t_stop.is_set():
            self.t_stop.wait(1)

            try:
                word = q.get()
                for engine in Multiscanner.get_engines():
                    self.get_links(word, engine)

            except Exception:
                pass
            finally:
                self.counter += 1
                q.task_done()

    def main(self):
        """ Prepare threads and launch main search"""
        for _ in xrange(self.threads):
            t = Thread(target=self.search, args=(self.q,))
            t.setDaemon(True)
            t.start()

        for word in open(self.dork_file):
            self.q.put(word.strip())

        try:
            while not self.t_stop.is_set():
                self.t_stop.wait(1)
                if self.counter == self.list_size:
                    self.t_stop.set()

        except KeyboardInterrupt:
            print '~ Sending signal to kill threads...'
            self.t_stop.set()
            exit(0)

        self.q.join()
        print 'Finished!'


if __name__ == "__main__":
    banner = '''
__    __  ___       ____  _                                       
__   /  |/  /__  __/ / /_(_)______________ _____  ____  ___  _____
__  / /|_/ // / / / / __/ // ___/ ___/ __ `/ __ \/ __ \/ _ \/ ___/
__ / /  / // /_/ / / /_/ /(__  ) /__/ /_/ / / / / / / /  __/ /    
__/_/  /_/ \__,_/_/\__/_//____/\___/\__,_/_/ /_/_/ /_/\___/_/              
by @kyxrec0n                                                              


    '''

    parser = argparse.ArgumentParser(description='Multiscanner by@kyxrec0n')

    parser.add_argument(
        '-f', '--file',
        action='store',
        dest='dork_file',
        help='List with dorks to scan',
        required=True
    )
    parser.add_argument(
        '-o', '--output',
        action='store',
        dest='output',
        help='Output to save valid results',
        default='output.txt'
    )
    parser.add_argument(
        '-t', '--threads',
        action='store',
        default=1,
        dest='threads',
        help='Concurrent workers ',
        type=int
    )
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()

    if args.dork_file:
        if not os.path.isfile(args.dork_file):
            exit('File {} not found'.format(args.dork_file))

        print banner
        multi_searcher = Multiscanner(
            args.dork_file,
            args.output,
            args.threads
        )
        multi_searcher.main()

