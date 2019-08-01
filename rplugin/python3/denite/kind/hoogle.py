from collections import defaultdict
import re

from .base import Base

TYPE_IDENTIFIER_RE = re.compile(r"\b[A-Z][a-zA-Z0-9_']*\b")

def _paste(vim, text):
    old_reg = [vim.call('getreg', '"'), vim.call('getregtype', '"')]

    vim.call('setreg', '"', text, "v")
    try:
        vim.command('normal! ""P')
    finally:
        vim.call('setreg', '"', old_reg[0], old_reg[1])

    # Open folds
    vim.command('normal! zv')


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
        imports_by_module = defaultdict(lambda: (list(), list(), list()))
        for target in context["targets"]:
            if "action__package" in target:
                raise NotImplementedError( "Can't import a package as a whole! Try selecting a module from this package instead?")
            elif "action__module" in target:
                module = target["action__module"]
                module_abbr = module.split(".")[-1][:1].upper()
                imports_by_module[module][0].append("import qualified {} as {}\n".format(module, module_abbr))
            elif "action__data" in target:
                d = target["action__data"]
                imports_by_module[d["module"]][1].append("{}(..)".format(_import_type_identifier_for_pattern(d["pattern"])))
            elif "action__class" in target:
                d = target["action__class"]
                imports_by_module[d["module"]][1].append(_import_type_identifier_for_pattern(d["pattern"]))
            elif "action__type" in target:
                d = target["action__type"]
                imports_by_module[d["module"]][1].append(_import_type_identifier_for_pattern(d["pattern"]))
            elif "action__value" in target:
                d = target["action__value"]
                imports_by_module[d["module"]][2].append(d["identifier"])
            else:
                raise NotImplementedError("Don't know how to format {} as an import".format(target["word"]))

        imports_by_module_items = list(imports_by_module.items())
        # reverse here and paste everything backwards since we're using P not p
        imports_by_module_items.sort(key=lambda t: t[0], reverse=True)
        for module, (module_imports, type_imports, value_imports) in imports_by_module_items:
            # type and value imports don't get sorted backwards since they'll be composed normally before P'd into the buffer
            type_imports.sort()
            value_imports.sort()
            if type_imports or value_imports:
                _paste(self.vim, "import {module} ({items})\n".format(module=module, items=", ".join(type_imports + value_imports)))

            module_imports.sort(reverse=True)
            for module_import in module_imports:
                _paste(self.vim, module_import)

