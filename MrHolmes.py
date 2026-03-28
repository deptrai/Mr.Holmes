#!/usr/bin/python3
# ORIGINAL CREATOR: Luca Garofalo (Lucksi)
# AUTHOR: Luca Garofalo (Lucksi)
# Copyright (C) 2021-2023 Lucksi <lukege287@gmail.com>
# License: GNU General Public License v3.0

import os
from Core.Support import Menu
from Core.Support import Font
from Core.Support import Language

filename = Language.Translation.Get_Language()
filename

class Main:

    @staticmethod
    def Controll_Display():
        Interface_file = "Display/Display.txt"
        if os.path.isfile(Interface_file):
            d = open(Interface_file,"r",newline=None)
            conf = d.read().strip("\n")
            d.close()
            if conf == "Desktop":
                pass
            elif conf == "Mobile":
                pass
            else:
                print(Font.Color.RED + "[!]" + Font.Color.WHITE +  Language.Translation.Translate_Language(filename, "Default", "DisplayError", "None"))
                exit()
        else:
             print(Font.Color.RED + "[!]" + Font.Color.WHITE + Language.Translation.Translate_Language(filename, "Default", "NoDisplay", "None") .format(Interface_file))
        return conf

    def Menu(Mode):
        Menu.Main.main(Mode)

if __name__ == "__main__":
    # --- Batch (non-interactive) mode — AC1, AC2, AC3 -------------------
    from Core.cli.parser import parse_args, has_batch_target, has_export_target
    from Core.cli.runner import BatchRunner

    _args = parse_args()

    # --- Export mode (Story 6.4 / 6.5 AC1) — highest priority -----------
    if has_export_target(_args):
        from Core.cli.parser import parse_investigation_ids

        try:
            inv_ids = parse_investigation_ids(_args.investigation)
        except Exception as exc:
            print(f"[!] {exc}")
            raise SystemExit(1)

        if _args.export == "pdf":
            from Core.reporting.pdf_export import PdfExporter

            # PDF supports a single investigation only
            single_id = inv_ids[0] if inv_ids else None
            if single_id is None:
                print("[!] PDF export does not support 'all' — specify a single ID.")
                raise SystemExit(1)
            try:
                out_path = PdfExporter().export(single_id)
                print(f"[✓] PDF exported: {out_path}")
                raise SystemExit(0)
            except ValueError as exc:
                print(f"[!] Export error: {exc}")
                raise SystemExit(1)
            except (ImportError, RuntimeError) as exc:
                print(f"[!] Export failed: {exc}")
                raise SystemExit(2)

        elif _args.export == "csv":
            from Core.reporting.csv_export import CsvExporter

            try:
                out_path = CsvExporter().export(inv_ids)  # None = all
                count_label = "all" if inv_ids is None else str(len(inv_ids))
                print(f"[✓] CSV exported ({count_label} investigation(s)): {out_path}")
                raise SystemExit(0)
            except ValueError as exc:
                print(f"[!] Export error: {exc}")
                raise SystemExit(1)
            except OSError as exc:
                print(f"[!] File error: {exc}")
                raise SystemExit(2)

    elif getattr(_args, "export", None) and not getattr(_args, "investigation", None):
        print("[!] --export requires --investigation <ID>. Example:")
        print("    python3 MrHolmes.py --export csv --investigation 1")
        print("    python3 MrHolmes.py --export csv --investigation all")
        raise SystemExit(1)

    if has_batch_target(_args):
        # One or more scan flags provided → run non-interactively
        runner = BatchRunner(_args)
        raise SystemExit(runner.run())

    # --- Interactive mode (no args) — backward compatible (AC3) ----------
    Mode = Main.Controll_Display()
    try:
        Main.Menu(Mode)
    except KeyboardInterrupt:
        print(Font.Color.RED + "\n\n[!]" + Font.Color.WHITE + Language.Translation.Translate_Language(filename, "Default", "KeyC", "None"))
        raise SystemExit(0)
    except ModuleNotFoundError as Error:
        print(Font.Color.RED + "\n\n[!]" + Font.Color.WHITE + Language.Translation.Translate_Language(filename, "Default", "Internal", "None").format(str(Error)))
        raise SystemExit(1)

