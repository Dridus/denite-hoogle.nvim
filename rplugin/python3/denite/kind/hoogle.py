import re

from .base import Base

TYPE_IDENTIFIER_RE = re.compile(r"\b[A-Z][a-zA-Z0-9_']*\b")

def _import_type_identifier_for_pattern(pattern):
    m = TYPE_IDENTIFIER_RE.match(pattern)
    if m:
        return m.group(0)
    else:
        return pattern

class Kind(Base):
    def __init__(self, vim):
        super().__init__(vim)

        self.name = "hoogle"
        self.default_action = "append"
        self.persistent_actions = ["open_link"]

    def action_open_link(self, context):
        for target in context["targets"]:
            if target["action__href"]:
                self.vim.call("denite#util#open", target["action__href"])
            else:
                self.error_message(context, "No link parsed from hoogle for {}. Did you customize default_opts and not pass --link?".format(target["word"]))

    def action_insert_import(self, context):
        for target in context["targets"]:
            import_text = None
            if "action__package" in target:
                self.error_message(context, "Can't import a package as a whole! Try selecting a module from this package instead?")
            elif "action__module" in target:
                module = target["action__module"]
                module_abbr = module.split(".")[-1][:1].upper()
                import_text = "import qualified {} as {}\n".format(module, module_abbr)
            elif "action__data" in target:
                d = target["action__data"]
                import_text = "import {module} ({identifier}(..))\n".format(identifier=_import_type_identifier_for_pattern(d["pattern"]), **d)
            elif "action__class" in target:
                d = target["action__class"]
                import_text = "import {module} ({identifier})\n".format(identifier=_import_type_identifier_for_pattern(d["pattern"]), **d)
            elif "action__type" in target:
                d = target["action__type"]
                import_text = "import {module} ({identifier})\n".format(identifier=_import_type_identifier_for_pattern(d["pattern"]), **d)
            elif "action__value" in target:
                d = target["action__value"]
                import_text = "import {module} ({identifier})\n".format(**d)
            else:
                raise NotImplementedError("Don't know how to format {} as an import".format(target["word"]))

            if import_text:
                old_reg = [self.vim.call('getreg', '"'), self.vim.call('getregtype', '"')]

                self.vim.call('setreg', '"', import_text, "v")
                try:
                    self.vim.command('normal! ""P')
                finally:
                    self.vim.call('setreg', '"', old_reg[0], old_reg[1])

                # Open folds
                self.vim.command('normal! zv')

