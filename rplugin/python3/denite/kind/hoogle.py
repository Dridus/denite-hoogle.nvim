from .base import Base

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
            if "action__module" in target and "action__symbol" in target:
                import_text = "import {action__module} ({action__symbol})\n".format(**target)
            elif "action__module" in target and "action__datatype" in target:
                import_text = "import {action__module} ({action__datatype}(..))\n".format(**target)
            elif "action__module" in target:
                module = target["action__module"]
                module_abbr = module.split(".")[-1][:1].upper()
                import_text = "import qualified {} as {}\n".format(module, module_abbr)
            else:
                self.error_message(context, "Don't know how to format {} as an import".format(target["word"]))

            if import_text:
                old_reg = [self.vim.call('getreg', '"'), self.vim.call('getregtype', '"')]

                self.vim.call('setreg', '"', import_text, "v")
                try:
                    self.vim.command('normal! ""P')
                finally:
                    self.vim.call('setreg', '"', old_reg[0], old_reg[1])

                # Open folds
                self.vim.command('normal! zv')

