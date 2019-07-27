import re

from .base import Base

from denite import util, process

SYNTAX = (
    r"syntax region deniteSource_hoogle start=// end=/$/ contained",
)

HIGHLIGHT = (
    r"syntax match deniteSource_hooglePackage /package\s\+/ contained containedin=deniteSource_hoogle nextgroup=deniteSource_hooglePackageName",
    r"syntax match deniteSource_hooglePackageName /\S\+/ contained",
    "highlight default link deniteSource_hooglePackage Keyword",
    "highlight default link deniteSource_hooglePackageName Typedef",

    r"syntax match deniteSource_hoogleModule /module\s\+/ contained containedin=deniteSource_hoogle nextgroup=deniteSource_hoogleModuleName",
    r"syntax match deniteSource_hoogleModuleName /\S\+/ contained contains=deniteMatchedRange",
    "highlight default link deniteSource_hoogleModule Keyword",
    "highlight default link deniteSource_hoogleModuleName Typedef",

    r"syntax match deniteSource_hoogleData /\S\+\s\+data\s\+.*/ contained keepend containedin=deniteSource_hoogle contains=deniteSource_hoogleDataModule",
    r"syntax match deniteSource_hoogleDataModule /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleDataKeyword",
    r"syntax match deniteSource_hoogleDataKeyword /data\s\+/ contained contains=deniteMatchRange nextgroup=deniteSource_hoogleDataSymbol",
    r"syntax match deniteSource_hoogleDataSymbol /.*/ contained contains=deniteMatchedRange",
    "highlight default link deniteSource_hoogleDataKeyword Keyword",
    "highlight default link deniteSource_hoogleDataModule Typedef",
    "highlight default link deniteSource_hoogleDataSymbol Identifier",

    r"syntax match deniteSource_hoogleSig /\S\+\s\+.\{-}\s\+::\s\+.*/ contained containedin=deniteSource_hoogle keepend contains=deniteSource_hoogleSigModule",
    r"syntax match deniteSource_hoogleSigModule /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleSigIdentifier",
    r"syntax match deniteSource_hoogleSigIdentifier /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleSigType",
    r"syntax match deniteSource_hoogleSigType /::\s\+.*/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleSigType",
    "highlight default link deniteSource_hoogleSigModule Typedef",
    "highlight default link deniteSource_hoogleSigIdentifier Identifier",
    "highlight default link deniteSource_hoogleSigType Typedef",
)

PACKAGE_RE = re.compile(r"package (\S+)")
MODULE_RE = re.compile(r"module (\S+)")
DATA_RE = re.compile(r"(\S+) data (.*)")
SIG_RE = re.compile(r"(\S+) (.*?) :: (.*)")
HREF_SPLIT_RE = re.compile(r"(.*?) -- ((?:http|file).*)")

class Source(Base):
    def __init__(self, vim):
        Base.__init__(self, vim)

        self.name = "hoogle"
        self.kind = "hoogle"
        self.vars = {
            "command": ["hoogle"],
            "default_opts": ["--count=100", "--link"],
            "min_interactive_pattern": 3,
        }
        self.is_volatile = True

    def on_init(self, context):
        context["__proc"] = None
        context["is_interactive"] = True

    def on_close(self, context):
        if context["__proc"]:
            context["__proc"].kill()
            context["__proc"] = None

    def highlight(self):
        for com in HIGHLIGHT:
            self.vim.command(com)
        for com in SYNTAX:
            self.vim.command(com)

    def define_syntax(self):
        pass

    def gather_candidates(self, context):
        if context["event"] == "interactive":
            self.on_close(context)

        if context["__proc"]:
            self.print_message(context, "have async")
            return self._async_gather_candidates(context, context["async_timeout"])

        if not self.vars["command"]:
            self.print_message(context, "no command")
            return []

        args = [util.expand(self.vars["command"][0])]
        args += self.vars["command"][1:]
        args += self.vars["default_opts"]
        if context["input"]:
            args += util.split_input(context["input"])

        self.print_message(context, args)

        context["__proc"] = process.Process(args, context, context["path"])
        return self._async_gather_candidates(context, 0.5)

    def _async_gather_candidates(self, context, timeout):
        outs, errs = context["__proc"].communicate(timeout=timeout)
        if errs:
            self.error_message(context, errs)
        context["is_async"] = not context["__proc"].eof()
        if context["__proc"].eof():
            context["__proc"] = None

        candidates = []
        for line in outs:
            m = HREF_SPLIT_RE.fullmatch(line)
            if m:
                pre, href = m.groups()
            else:
                pre, href = line, None

            candidate = None

            if not candidate:
                m = PACKAGE_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__package": m.group(1), "action__href": href}

            if not candidate:
                m = MODULE_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__module": m.group(1), "action__href": href}

            if not candidate:
                m = DATA_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__module": m.group(1), "action__datatype": m.group(2), "action__href": href}

            if not candidate:
                m = SIG_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__module": m.group(1), "action__symbol": m.group(2), "action__type": m.group(3), "action__href": href}

            if not candidate:
                candidate = {"word": pre, "action__href": href}

            candidates.append(candidate)

        return candidates

