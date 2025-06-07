
from .gitService import GitService, Commit
from .logger import Logger

import inquirer
import enum


class ViewState(enum.Enum):

    QUIT: int = -1
    NONE: int = 0
    MAIN: int = 1
    INFO: int = 2
    EDIT_MENU: int = 3
    EDIT_MANUAL: int = 6
    EDIT_BATCH: int = 8

    def __str__(self) -> str:
        return f"ViewState.{self.name} ({self.value})"



class ViewHelper:

    MAIN_TITLE: str = '\n'.join([
        f"   ___ _ _       ___ _                             ",
        f"  / _ (_) |_    / __\ | ___  __ _ _ __   ___ _ __  ",
        f" / /_\/ | __|  / /  | |/ _ \/ _` | '_ \ / _ \ '__| ",
        f"/ /_\\\| | |_  / /___| |  __/ (_| | | | |  __/ |   ",
        f"\____/|_|\__| \____/|_|\___|\__,_|_| |_|\___|_|    ",
        f"                                                   ",
        f"            Made with ❤  by nowi ^w^              ",
    ])
    SEPARATOR: str = '=' * 50
    APP_NAME: str = "Git Cleaner"
    APP_VERSION: str = "0.1"
    FOUND: str = "\033[92mFound\033[0m"
    NOT_FOUND: str = "\033[91mNot Found\033[0m"
    INFO_BALISE: str = "[\033[93mi\033[0m]"
    USER_INTERACTION_BALISE: str = "[\033[92m>\033[0m]"
    ERROR_BALISE: str = "[\033[91mX\033[0m]"
    GTIHUBLINK: str = "https://github.com/Ant0in"

    @staticmethod
    def InquireCommit(message: str, commits: list[Commit]) -> Commit | None:

        questions: list = [
            inquirer.List(
                'commit',
                message=message,
                choices=[commit for commit in commits] + ["Back"],
            ),
        ]

        answer: Commit | str = inquirer.prompt(questions).get('commit', None)
        return answer if answer != "Back" else None

    @staticmethod
    def Inquire(message: str, choices: dict[str: ViewState]) -> ViewState:

        questions: list = [
            inquirer.List(
                'choice',
                message=message,
                choices=choices.keys(),
            ),
        ]

        answers: dict = inquirer.prompt(questions)
        return choices[answers['choice']]

    @staticmethod
    def InquireSingle(message: str) -> str:
        question: list = [
            inquirer.Text(
                'input',
                message=message,
                validate=lambda _, x: x != '',
            )
        ]
        userinput: str = inquirer.prompt(question)['input']
        print(userinput)
        return userinput.strip() 

    @staticmethod
    def Flush() -> None:
        # let's use Escape Sequences to clear the console
        print("\033[H\033[J", end='')

    @staticmethod
    def Title() -> None:
        print(ViewHelper.MAIN_TITLE, end='\n\n')
        print(f"{ViewHelper.INFO_BALISE} Version: v{ViewHelper.APP_VERSION}")

    @staticmethod
    def GitStatus(service: GitService) -> None:
        userHasGit: bool = service.doesUserHaveGit()
        print(f"{ViewHelper.INFO_BALISE} Git status: {ViewHelper.FOUND if userHasGit else ViewHelper.NOT_FOUND}\n")

    @staticmethod
    def Main(view: 'View') -> ViewState:
        ViewHelper.Title()
        ViewHelper.GitStatus(view.git)
        return ViewHelper.Inquire("Select an option", {
            "Edit": ViewState.EDIT_MENU,
            "Informations": ViewState.INFO,
            "Quit": ViewState.QUIT 
        })
    
    @staticmethod
    def Info(view: 'View') -> ViewState:
        
        ViewHelper.Title()
        ViewHelper.GitStatus(view.git)

        print(f"{ViewHelper.INFO_BALISE} Developped by nowi ^w^")
        print(f"{ViewHelper.INFO_BALISE} Version: {ViewHelper.APP_VERSION}")
        print(f"{ViewHelper.INFO_BALISE} GitHub: {ViewHelper.GTIHUBLINK}")

        input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to return to the edit menu... ")
        return ViewState.MAIN

    @staticmethod   
    def EditMenu(view: 'View') -> ViewState:
        
        ViewHelper.Title()
        ViewHelper.GitStatus(view.git)

        fp: str = view.currentGitFolder
        if view.currentGitFolder is None:
            fp: str = ViewHelper.InquireSingle('Enter the path to the git repository')
        found: bool = view.git.isFolderAGitRepository(fp)

        print(f"\n{ViewHelper.INFO_BALISE} Git Folder @ '{fp}': {ViewHelper.FOUND if found else ViewHelper.NOT_FOUND}")
        state: ViewState = ViewHelper.Inquire("Select an option", {
            "Edit in Batch": ViewState.EDIT_BATCH,
            "Edit Manually": ViewState.EDIT_MANUAL,
            "Back": ViewState.MAIN 
        })

        if state == ViewState.MAIN:
            view.removeCurrentGitFolder()
            return state

        if not found:
            print(f"{ViewHelper.ERROR_BALISE} The folder '{fp}' is not a valid git repository.")
            input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to continue... ")
            return ViewState.MAIN
    
        else:
            view.setCurrentGitFolder(fp)
            return state
    
    @staticmethod
    def EditManual(view: 'View') -> ViewState:

        ViewHelper.Title()
        ViewHelper.GitStatus(view.git)

        print(f"{ViewHelper.INFO_BALISE} Current Git Folder: {view.currentGitFolder}")

        commits: list[Commit] = view.git.getCommits(view.currentGitFolder)
        if not commits:
            print(f"{ViewHelper.INFO_BALISE} No commits found in the current git folder.")
            input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to return to the edit menu... ")
            view.removeCurrentGitFolder()
            return ViewState.EDIT_MENU

        print(f"{ViewHelper.INFO_BALISE} Found {len(commits)} commits in the current git folder.")
        commit: Commit = ViewHelper.InquireCommit("Select a commit to edit", commits)

        if commit is None: return ViewState.EDIT_MENU
        else: return ViewHelper.EditManualSingle(view, commit)

    @staticmethod
    def EditManualSingle(view: 'View', commit: Commit) -> ViewState:
        name: str = ViewHelper.InquireSingle(f"Enter the new commit message for '{commit}'")
        view.git.renameCommit(view.currentGitFolder, commit.hashstr, name)
        return ViewState.EDIT_MANUAL

    @staticmethod
    def EditBatch(view: 'View') -> ViewState:
        
        ViewHelper.Title()
        ViewHelper.GitStatus(view.git)
        print(f"{ViewHelper.INFO_BALISE} Current Git Folder: {view.currentGitFolder}")

        targets: list[str] = list()

        while 1:
            userInput: str = ViewHelper.InquireSingle("Enter the words you wish to replace in the commit messages, use '.' to end the input")
            if userInput == '.': break
            else: targets.append(userInput.strip())

        if not targets:
            print(f"{ViewHelper.ERROR_BALISE} No targets provided, returning to the edit menu.")
            input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to continue... ")
            return ViewState.EDIT_MENU
        
        print(f"{ViewHelper.INFO_BALISE} Targets: {', '.join(targets)}")
        replacement: str = ViewHelper.InquireSingle("Enter the replacement string for the targets")

        commits: list[Commit] = view.git.getCommits(view.currentGitFolder)
        if not commits:
            print(f"{ViewHelper.INFO_BALISE} No commits found in the current git folder.")
            input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to return to the edit menu... ")
            return ViewState.EDIT_MENU
        
        print(f"{ViewHelper.INFO_BALISE} Found {len(commits)} commits in the current git folder.")
        
        ret: list[Commit] = list()
        for commit in commits:

            newMessage: str = commit.name
            for target in targets:
                if target in commit.name:
                    newMessage = newMessage.replace(target, replacement)
            
            if newMessage != commit.name:
                ret.append(Commit(newMessage, commit.hashstr))

        if not ret:
            print(f"{ViewHelper.INFO_BALISE} No commits were modified.")
            input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to return to the edit menu... ")
            return ViewState.EDIT_MENU
        
        print(f"{ViewHelper.INFO_BALISE} {len(ret)} commits will be modified.")
        print(ret, [i.hashstr for i in ret], [i.name for i in ret])
        view.git.renameCommits(view.currentGitFolder, [i.hashstr for i in ret], [i.name for i in ret])

        print(f"{ViewHelper.INFO_BALISE} Commits modified successfully.")
        input(f"{ViewHelper.USER_INTERACTION_BALISE} Press Enter to return to the edit menu... ")
        return ViewState.EDIT_MENU



class View:

    def __init__(self, state: ViewState = ViewState.MAIN, log: bool = False) -> None:
        self._state: ViewState = state
        self._git: GitService = GitService(Logger() if log else None)
        self._currentGitFolder: str | None = None

    @property
    def state(self) -> ViewState:
        return self._state

    def setState(self, state: ViewState) -> None:
        self._state = state

    @property
    def git(self) -> GitService:
        return self._git

    @property
    def currentGitFolder(self) -> str | None:
        return self._currentGitFolder
    
    def setCurrentGitFolder(self, folder: str) -> None:
        self._currentGitFolder = folder

    def removeCurrentGitFolder(self) -> None:
        self._currentGitFolder = None

    def display(self) -> None:

        while self.state != ViewState.QUIT:
            
            ViewHelper.Flush()
            ret: ViewState = ViewState.NONE

            match self.state:
                case ViewState.MAIN: ret: ViewState = ViewHelper.Main(self)
                case ViewState.INFO: ret: ViewState = ViewHelper.Info(self)
                case ViewState.EDIT_MENU: ret: ViewState = ViewHelper.EditMenu(self)
                case ViewState.EDIT_MANUAL: ret: ViewState = ViewHelper.EditManual(self)
                case ViewState.EDIT_BATCH: ret: ViewState = ViewHelper.EditBatch(self)
                case _: raise NotImplementedError(f"ViewState {self.state} is not implemented.")

            if ret: self.setState(ret)

