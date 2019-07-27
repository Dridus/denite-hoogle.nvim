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
    r"syntax match deniteSource_hoogleDataKeyword /data\s\+/ contained contains=deniteMatchRange nextgroup=deniteSource_hoogleDataPattern",
    r"syntax match deniteSource_hoogleDataPattern /.*/ contained contains=deniteMatchedRange",
    "highlight default link deniteSource_hoogleDataKeyword Keyword",
    "highlight default link deniteSource_hoogleDataModule Typedef",
    "highlight default link deniteSource_hoogleDataPattern Identifier",

    r"syntax match deniteSource_hoogleClass /\S\+\s\+class\s\+.*/ contained keepend containedin=deniteSource_hoogle contains=deniteSource_hoogleClassModule",
    r"syntax match deniteSource_hoogleClassModule /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleClassKeyword",
    r"syntax match deniteSource_hoogleClassKeyword /class\s\+/ contained contains=deniteMatchRange nextgroup=deniteSource_hoogleClassPattern",
    r"syntax match deniteSource_hoogleClassPattern /.*/ contained contains=deniteMatchedRange",
    "highlight default link deniteSource_hoogleClassKeyword Keyword",
    "highlight default link deniteSource_hoogleClassModule Typedef",
    "highlight default link deniteSource_hoogleClassPattern Identifier",

    r"syntax match deniteSource_hoogleType /\S\+\s\+type\s\+.\{-1,}\s\+=\s\+.*/ contained keepend containedin=deniteSource_hoogle contains=deniteSource_hoogleTypeModule",
    r"syntax match deniteSource_hoogleTypeModule /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleTypeKeyword",
    r"syntax match deniteSource_hoogleTypeKeyword /type\s\+/ contained contains=deniteMatchRange nextgroup=deniteSource_hoogleTypePattern",
    r"syntax match deniteSource_hoogleTypePattern /[^=]\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleTypeEquate",
    r"syntax match deniteSource_hoogleTypeEquate /=\s\+/ contained nextgroup=deniteSource_hoogleTypeTarget",
    r"syntax match deniteSource_hoogleTypeTarget /.*/ contained contains=deniteMatchedRange",
    "highlight default link deniteSource_hoogleTypeModule Typedef",
    "highlight default link deniteSource_hoogleTypeEquate Operator",
    "highlight default link deniteSource_hoogleTypeKeyword Keyword",
    "highlight default link deniteSource_hoogleTypePattern Identifier",

    r"syntax match deniteSource_hoogleValue /\S\+\s\+.\{-1,}\s\+::\s\+.*/ contained containedin=deniteSource_hoogle keepend contains=deniteSource_hoogleValueModule",
    r"syntax match deniteSource_hoogleValueModule /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleValueIdentifier",
    r"syntax match deniteSource_hoogleValueIdentifier /\S\+\s\+/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleValueType",
    r"syntax match deniteSource_hoogleValueType /::\s\+.*/ contained contains=deniteMatchedRange nextgroup=deniteSource_hoogleValueType",
    "highlight default link deniteSource_hoogleValueModule Typedef",
    "highlight default link deniteSource_hoogleValueIdentifier Identifier",
    "highlight default link deniteSource_hoogleValueType Typedef",
)

PACKAGE_RE = re.compile(r"package (\S+)")
MODULE_RE = re.compile(r"module (\S+)")
DATA_RE = re.compile(r"(\S+) data (.*)")
CLASS_RE = re.compile(r"(\S+) class (.*)")
TYPE_RE = re.compile(r"(\S+) type (.*?) = (.*)")
VALUE_RE = re.compile(r"(\S+) (.*?) :: (.*)")
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
            try:
                self.vim.command(com)
            except:
                self.debug("Raised exception running highlight command: {}".format(com))
                raise

    def define_syntax(self):
        for com in SYNTAX:
            try:
                self.vim.command(com)
            except:
                self.debug("Raised exception running syntax command: {}".format(com))
                raise

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
            if "|" in context["input"]:
                args += util.split_input(context["input"].split("|")[0])
            else:
                args += [util.split_input(context["input"])[0]]

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
                    candidate = {"word": pre, "action__data": {"module": m.group(1), "pattern": m.group(2)}, "action__href": href}

            if not candidate:
                m = CLASS_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__class": {"module": m.group(1), "pattern": m.group(2)}, "action__href": href}

            if not candidate:
                m = TYPE_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__type": {"module": m.group(1), "pattern": m.group(2), "target" : m.group(3)}, "action__href": href}

            if not candidate:
                m = VALUE_RE.fullmatch(pre)
                if m:
                    candidate = {"word": pre, "action__value": {"module": m.group(1), "identifier": m.group(2), "type": m.group(3)}, "action__href": href}

            if not candidate:
                candidate = {"word": pre, "action__href": href}

            candidates.append(candidate)

        return candidates

