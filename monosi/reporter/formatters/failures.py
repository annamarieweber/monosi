from .base import BaseFormatter

class FailureListFormatter(BaseFormatter):
    def example_failed(self, failure):
        self.write("{location}:{description}".format(
            location=failure.example.location, 
            description=failure.example.description
        ), Color.RED)