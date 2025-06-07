
import enum
import sys
import time
import uuid


class LogLevel(enum.Enum):

    NONE: str = "NONE"
    DEBUG: str = "DEBUG"
    INFO: str = "INFO"
    WARNING: str = "WARNING"
    ERROR: str = "ERROR"
    CRITICAL: str = "CRITICAL"

    def __str__(self) -> str:
        return self.value
    
 
class Logger:

    # Singleton variables
    _instance: object | None = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs) -> "Logger":
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self, description: str = "Logger") -> None:

        # Ensure that the logger is only initialized once
        if self._initialized: return

        self._description: str = description
        self._date: str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self._uuid: str = str(uuid.uuid4())

    @property
    def description(self) -> str:
        return self._description
    
    @property
    def date(self) -> str:
        return self._date

    @property
    def uuid(self) -> str:
        return self._uuid

    def consoleLog(self, content: str, level: LogLevel | None = LogLevel.NONE) -> None:

        """
        Logs messages to the console with a specified log level.
        Args:
            content (str): The message to log.
            level (LogLevel): The log level for the message.
        """

        assert isinstance(content, str), "Content must be a string."
        assert isinstance(level, LogLevel), "Level must be an instance of LogLevel."

        fromattedContent: str = f"[{self.description}] [{level}] {content}" if level != LogLevel.NONE else f"[{self.description}] {content}"
        print(fromattedContent, file=sys.stderr if level in {LogLevel.ERROR, LogLevel.CRITICAL} else sys.stdout)

    def logWarning(self, content: str) -> None:
        self.consoleLog(content, LogLevel.WARNING)

    def logError(self, content: str) -> None: 
        self.consoleLog(content, LogLevel.ERROR)

    def logCritical(self, content: str) -> None:
        self.consoleLog(content, LogLevel.CRITICAL)

    def logDebug(self, content: str) -> None:
        self.consoleLog(content, LogLevel.DEBUG)

    def logInfo(self, content: str) -> None:
        self.consoleLog(content, LogLevel.INFO)

    def log(self, content: str) -> None:
        self.consoleLog(content, LogLevel.NONE)

    def __del__(self) -> None:
        
        """
        Destructor to clean up the logger instance.
        """

        self._instance = None
        self._initialized = False
    
    def __repr__(self) -> str:
        return f"Logger(description={self.description}, date={self.date})"
    
    def __str__(self) -> str:
        return f"Logger: {self.description} | Date: {self.date}"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Logger):
            self.logWarning("Comparison with non-Logger object.")
            return False
        return self.uuid == other.uuid
    
