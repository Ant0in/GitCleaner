
from .logger import Logger

import sys
import subprocess
import pathlib
import tempfile
import os
import json 


class Commit:

    def __init__(self, name: str, hashstr: str) -> None:
        self._name: str = name
        self._hashstr: str = hashstr

    @classmethod
    def fromString(cls, commit_str: str) -> "Commit":

        """
        Creates a Commit object from a string representation of a commit.
        Args:
            commit_str (str): The string representation of the commit, expected format is "hash name".
        Returns:
            Commit: A Commit object with the name and hashstr extracted from the string.
        Raises:
            ValueError: If the commit string is not in the expected format.
        """
        
        parts: list[str] = commit_str.split(' ', 1)
        if len(parts) == 2:
            return cls(name=parts[1].strip('"'), hashstr=parts[0].strip('"'))
        raise ValueError("Invalid commit string format. Expected 'hash name' format.")

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def hashstr(self) -> str:
        return self._hashstr
    
    def __repr__(self) -> str:
        return f"Commit={self.name} (hash={self.hashstr})"

    def __str__(self) -> str:
        return f"{self.hashstr}, {self.name}"



class GitService:

    def __init__(self, logger: Logger | None = None) -> None:
        self.logger: Logger = logger

    @property
    def Logger(self) -> Logger | None:
        return self.logger

    def hasLogger(self) -> bool:
        return self.logger is not None

    def runGitCommand(self, command: list[str], env: any = None,
                      stdout: int | None = None, stderr: int | None = None) -> subprocess.CompletedProcess:

        try:

            assert isinstance(command, list), "Command must be a list of strings."
            assert all(isinstance(arg, str) for arg in command), "All command arguments must be strings."

            stdout = stdout if stdout else subprocess.PIPE
            stderr = stderr if stderr else subprocess.PIPE

            result: subprocess.CompletedProcess = subprocess.run(command, stdout=stdout, stderr=stderr, env=env)

            if self.hasLogger():
                if result.returncode == 0: self.logger.logInfo(f"Command executed successfully: {' '.join(command)}")
                else: self.logger.logError(f"Command failed with error: {result.stderr.decode('utf-8', errors='ignore')}")

            return result
        
        except Exception as e:
            if self.hasLogger(): self.logger.logError(f"An error occurred while running the command: {e}")
            raise e

    def doesUserHaveGit(self) -> bool:

        """
        Checks if the user has git installed on their system.
        Returns:
            bool: True if git is installed, False otherwise.
        """

        USER_ON_WINDOWS: bool = sys.platform.startswith('win')
        pipe: list[str] = ['git', '--version'] if USER_ON_WINDOWS else ['which', 'git']
        
        try:
            result: subprocess.CompletedProcess = self.runGitCommand(pipe)
            return result.returncode == 0
        except: return False

    def isFolderAGitRepository(self, fp: str) -> bool:
        
        """
        Checks if the specified folder is a git repository.
        Args:
            folderPath (str): The path to the folder to check.
        Returns:
            bool: True if the folder is a git repository, False otherwise.
        """

        try:
            result: subprocess.CompletedProcess = self.runGitCommand(
                ['git', '-C', str(pathlib.Path(fp).resolve()), 'rev-parse', '--is-inside-work-tree']
            )
            return result.returncode == 0 and result.stdout.strip() == b'true'
        except:
            return False

    def getCommits(self, fp: str) -> list[Commit]:
        
        """
        Retrieves the names of commits in the specified git repository.
        Args:
            folderPath (str): The path to the git repository.
        Returns:
            list[str]: A list of commit names.
        """

        result: subprocess.CompletedProcess = self.runGitCommand(['git', '-C', fp, 'log', '--pretty=format:"%h %s"'])
        commits: list[Commit] = list()

        if result.returncode == 0:
                
            lines: list[str] = result.stdout.decode('utf-8').strip().split('\n')
            for line in lines:
                try:
                    commit: Commit = Commit.fromString(line)
                    commits.append(commit)
                except ValueError as ve:
                    if self.hasLogger(): self.logger.logWarning(f"Skipping invalid commit line: {line} - {ve}")

        return commits
    
    def abortRebase(self, fp: str) -> None:
        self.runGitCommand(['git', '-C', fp, 'rebase', '--abort'])

    def renameCommits(self, fp: str, targets: list[str], names: list[str]) -> None:

        commits: list[Commit] = self.getCommits(fp)
        changeDict: dict[str: str] = {t[:7]: n for t, n in zip(targets, names, strict=True)}
        targetHash: set[str] = set(changeDict.keys())

        subset: list[str] = []
        seen = set()
        for c in commits:
            h = c.hashstr[:7]
            subset.append(c)
            if h in targetHash:
                seen.add(h)
            if seen == targetHash:
                break
        subset.reverse()

        lines: list[str] = list()
        for c in subset:
            if c.hashstr in targets: lines.append(f"reword {c.hashstr[:7]} {c.name}")
            else: lines.append(f"pick {c.hashstr[:7]} {c.name}")
        # Create a temporary file to store the todo list for the rebase
        todo_file = tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8')
        todo_file.write('\n'.join(lines))
        todo_file.close()

        # Create a sequence editor
        seq_editor_script = tempfile.NamedTemporaryFile('w', delete=False, suffix='.py', encoding='utf-8')
        script: str = f"import sys\ntodo_path = r\"{todo_file.name}\"\nwith open(sys.argv[1], 'w', encoding='utf-8') as out, open(todo_path, 'r', encoding='utf-8') as inp: out.write(inp.read())"""
        seq_editor_script.write(script)
        seq_editor_script.close()

        # Write the new names into another temporary file
        msg_file = tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8')
        json.dump(names, msg_file)
        msg_file.close()

        # Manage GIT EDITOR (replace commit editmsg)
        editor_script = tempfile.NamedTemporaryFile('w', delete=False, suffix='.py', encoding='utf-8')
        editor_script.write(
            f"import sys, json\n"
            f"path = sys.argv[1]\n"
            f"queue_path = r\"{msg_file.name}\"\n"
            f"with open(queue_path, 'r+', encoding='utf-8') as f:\n"
            f"    msgs = json.load(f)\n"
            f"    if not msgs:\n"
            f"        exit(0)\n"
            f"    msg = msgs.pop(0)\n"
            f"    f.seek(0); f.truncate(); json.dump(msgs, f)\n"
            f"with open(path, 'w', encoding='utf-8') as f:\n"
            f"    f.write(msg)\n"
        )
        editor_script.close()

        # Prepare the environment for the git command
        env = os.environ.copy()
        env['GIT_SEQUENCE_EDITOR'] = f'python "{seq_editor_script.name}"'
        env['GIT_EDITOR'] = f'python "{editor_script.name}"'

        first: str = subset[0].hashstr[:7]
        self.runGitCommand(['git', '-C', fp, 'rebase', '-i', f'{first}^'], env=env)

        # Clean up temporary files
        os.remove(todo_file.name)
        os.remove(seq_editor_script.name)
        os.remove(msg_file.name)
        os.remove(editor_script.name)

    def renameCommit(self, fp: str, target: str, name: str) -> None:
        self.renameCommits(fp, [target], [name])

