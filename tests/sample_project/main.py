from base import BaseService
import utils

class mainService(BaseService):
    def run(self):
        utils.logger("Starting run")
        self.connect()
        utils.helper_func()
        self.process()
        self.disconnect()

    def process(self):
        print("Processing...")

def entry_point():
    s = mainService()
    s.run()

if __name__ == "__main__":
    entry_point()