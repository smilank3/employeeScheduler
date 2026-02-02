
import json
import tkinter as tk
from tkinter import ttk, messagebox



# CONSTANTS


DAYS            = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SHIFT_OPTIONS   = ["Off", "Morning", "Afternoon", "Evening"]   # dropdown choices
ACTUAL_SHIFTS   = ["Morning", "Afternoon", "Evening"]          # shifts that need staffing

# Colors ──
BG_APP          = "#f5f5f5"
BG_HEADER       = "#111213"
FG_HEADER       = "white"
BTN_ADD         = "#007bff"
BTN_ADD_HOVER   = "#0056b3"
BTN_GEN         = "#28a745"
BTN_GEN_HOVER   = "#1e7e34"
LABEL_PREF1     = "#28a745"    
LABEL_PREF2     = "#4a90d9"    
STATUS_OK       = "#28a745"     
STATUS_WARN     = "#e67e22"     
STATUS_FAIL     = "#dc3545"    





class ScrollableFrame(tk.Frame):
   

    def __init__(self, parent, fixed_height=None, **kwargs):
        super().__init__(parent, bg=BG_APP, **kwargs)

        # Canvas and  scrollbars
        self.canvas = tk.Canvas(self, bg=BG_APP, highlightthickness=0)

        self.v_scroll = ttk.Scrollbar(self, orient="vertical",   command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right",  fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.configure(yscrollcommand=self.v_scroll.set,
                              xscrollcommand=self.h_scroll.set)

        # Inner frame lives on the canvas
        self.inner = tk.Frame(self.canvas, bg=BG_APP)
        self._window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Fixed height 
        if fixed_height:
            self.pack_propagate(False)
            self.configure(height=fixed_height)

        # Mousewheel routing
        self.canvas.bind("<Enter>", lambda e: self._bind_scroll())
        self.canvas.bind("<Leave>", lambda e: self._unbind_scroll())

    # scroll 
    def _bind_scroll(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>",   self._scroll_up)    # Linux
        self.canvas.bind_all("<Button-5>",   self._scroll_down)  # Linux

    def _unbind_scroll(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_up(self, event):
        self.canvas.yview_scroll(-1, "units")

    def _scroll_down(self, event):
        self.canvas.yview_scroll(1, "units")

    def refresh(self):
        """Call after adding/removing widgets to update the scroll region."""
        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))



# main app



class ShiftScheduler:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Shift Scheduler")
        self.root.geometry("1350x900")
        self.root.minsize(1050, 650)
        self.root.configure(bg=BG_APP)

        # employees list
     
        self.employees: list[dict] = []

        #  holds the tk StringVars for each row.
    
        self._row_vars: list[dict] = []

        ttk.Style().theme_use("clam")         

        self._build_ui()
        self.add_employee_row()               # start with one blank row


    # LAYOUT
   

    def _build_ui(self):
        # Buttons 
        btn_bar = tk.Frame(self.root, bg=BG_APP)
        btn_bar.pack(fill="x", padx=22, pady=(14, 2))

        tk.Button(
            btn_bar, text="+ Add Employee", command=self.add_employee_row,
            bg=BTN_ADD, fg="white", activebackground=BTN_ADD_HOVER, activeforeground="white",
            font=("Consolas", 10, "bold"), relief="flat", padx=18, pady=7,
            bd=0, cursor="hand2"
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_bar, text="⚡ Generate Schedule", command=self.run_scheduler,
            bg=BTN_GEN, fg="white", activebackground=BTN_GEN_HOVER, activeforeground="white",
            font=("Consolas", 10, "bold"), relief="flat", padx=18, pady=7,
            bd=0, cursor="hand2"
        ).pack(side="left")

        # Preferences table 
        tk.Label(self.root, text="Employee Preferences",
                 font=("Consolas", 13, "bold"), bg=BG_APP, fg="#2c3e50"
                 ).pack(pady=(12, 4), anchor="w", padx=22)

        self.pref_scroll = ScrollableFrame(self.root, fixed_height=400)
        self.pref_scroll.pack(fill="x", padx=22, pady=(0, 6))
        self._build_pref_headers()

        # Schedule output 
        tk.Label(self.root, text="Weekly Schedule",
                 font=("Consolas", 13, "bold"), bg=BG_APP, fg="#2c3e50"
                 ).pack(pady=(12, 4), anchor="w", padx=22)

        self.sched_scroll = ScrollableFrame(self.root)
        self.sched_scroll.pack(fill="both", expand=True, padx=22, pady=(0, 14))

   
    # PREFERENCE TABLE HEADERS
   

    def _build_pref_headers(self):
        for col, text in enumerate(["Employee"] + DAYS):
            tk.Label(
                self.pref_scroll.inner, text=text,
                font=("Consolas", 10, "bold"),
                bg=BG_HEADER, fg=FG_HEADER,
                padx=6, pady=6, anchor="center", relief="flat"
            ).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)


    # ADD EMPLOYEE ROW
 

    def add_employee_row(self):
        index   = len(self.employees)          # position in the array
        row_idx = index + 1                    # grid row  (0 = headers)
        bg = "#f2f2f2" if row_idx % 2 == 0 else "#ffffff"

        #  Push a blank employee into the array
        self.employees.append({
            "name":         "",
            "prefs":        {day: ["Off", "Off"] for day in DAYS},
            "workDayCount": 0,
        })

        # Create StringVars and store them 
        name_var  = tk.StringVar()
        pref_vars = {day: (tk.StringVar(value="Off"),
                           tk.StringVar(value="Off")) for day in DAYS}

        self._row_vars.append({"name_var": name_var, "prefs": pref_vars})

        # Build the UI row
        # Name cell
        name_cell = tk.Frame(self.pref_scroll.inner, bg=bg)
        name_cell.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)

        tk.Entry(
            name_cell, textvariable=name_var,
            font=("Consolas", 10), width=17, relief="flat", bd=2,
            highlightthickness=1, highlightbackground="#ccc",
            highlightcolor="#007bff", bg="white"
        ).pack(padx=6, pady=5)

        # Day cells
        for day_col, day in enumerate(DAYS):
            p1_var, p2_var = pref_vars[day]

            cell = tk.Frame(self.pref_scroll.inner, bg=bg)
            cell.grid(row=row_idx, column=day_col + 1, sticky="nsew", padx=1, pady=1)

            tk.Label(cell, text="1st Pref", font=("Consolas", 8, "bold"),
                     fg=LABEL_PREF1, bg=bg, anchor="e"
                     ).pack(fill="x", padx=(2, 6), pady=(4, 0))
            ttk.Combobox(cell, textvariable=p1_var, values=SHIFT_OPTIONS,
                         state="readonly", width=11).pack(pady=(1, 2))

            tk.Label(cell, text="2nd Pref", font=("Consolas", 8, "bold"),
                     fg=LABEL_PREF2, bg=bg, anchor="e"
                     ).pack(fill="x", padx=(2, 6))
            ttk.Combobox(cell, textvariable=p2_var, values=SHIFT_OPTIONS,
                         state="readonly", width=11).pack(pady=(1, 4))

        self.pref_scroll.refresh()

  
    # DATA COLLECTION  &  VALIDATION

# Called right before validation + scheduling. 
    def _sync_employees(self):
      
        for i, row in enumerate(self._row_vars):
            emp = self.employees[i]

            # name
            emp["name"] = row["name_var"].get().strip()

            # prefs
            for day in DAYS:
                p1_var, p2_var = row["prefs"][day]
                emp["prefs"][day] = [p1_var.get(), p2_var.get()]

            # workDayCount
            unavailable          = sum(1 for d in DAYS if emp["prefs"][d][0] == "Off" and emp["prefs"][d][1] == "Off")
            emp["workDayCount"]  = 7 - unavailable

    @staticmethod
    def _validate(employees: list[dict]) -> list[str]:
    
        errors = []
        seen_names: set[str] = set()

        for i, emp in enumerate(employees):
            row_label = f"Row {i + 1}"

            # name checks missing
            if not emp["name"]:
                errors.append(f"{row_label}: Employee name is missing.")
           
            #  max 5 working days
            if emp["workDayCount"] > 5:
                label = emp["name"] or "unnamed"
                errors.append(f"{row_label} ({label}): Max 5 working days allowed.")

        return errors

  
    # SCHEDULING ALGORITHM 
  

    @staticmethod
    def _is_available(emp: dict, day: str, shift: str) -> bool:
       
        first, second = emp["prefs"][day]
        if first == "Off" and second == "Off":
            return False
        return first == shift or second == shift

    @staticmethod
    def _get_preference_rank(emp: dict, day: str, shift: str) -> int:
        first, second = emp["prefs"][day]
        if first  == shift: return 0
        if second == shift: return 1
        return -1

    def _fill_shift(self, day: str, shift: str,
                    pool: list[dict], assigned_days: dict) -> list[dict]:
        assigned: list[dict] = []

        #  eligible pool
        eligible = [
            emp for emp in pool
            if day not in assigned_days.get(emp["name"], set())                        # not already working today
            and len(assigned_days.get(emp["name"], set())) < emp["workDayCount"]        # under their day cap
            and self._is_available(emp, day, shift)                                    # listed this shift
        ]

        print(json.dumps(eligible,indent=1))

        #  preference rank
        eligible.sort(key=lambda e: (
            self._get_preference_rank(e, day, shift),
            len(assigned_days.get(e["name"], set()))
        ))

        # fewer total work-days = higher priority
    
        eligible.sort(key=lambda e: e["workDayCount"])

        # new list 
          #print(json.dumps(eligible,indent=2))

        # Assign top 2 
        for emp in eligible[:2]:
            rank = self._get_preference_rank(emp, day, shift)
            assigned.append({
                "name":   emp["name"],
                "choice": "pref1" if rank == 0 else "pref2",
            })
            assigned_days.setdefault(emp["name"], set()).add(day)

        return assigned

    def _generate_schedule(self, pool: list[dict]):
        schedule      = {}
        assigned_days = {}

        for day in DAYS:
            schedule[day] = {}
            for shift in ACTUAL_SHIFTS:
                schedule[day][shift] = self._fill_shift(day, shift, pool, assigned_days)

        return schedule, assigned_days


    # RUN  &  RENDER
 

    def run_scheduler(self):
        if not self.employees:
            messagebox.showwarning("No Employees", "Please add at least one employee first.")
            return

        # Sync UI 
        self._sync_employees()

        errors = self._validate(self.employees)
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        schedule, _ = self._generate_schedule(self.employees)
        print(json.dumps(schedule,indent=2))
        self._render_schedule(schedule)

    def _render_schedule(self, schedule: dict):
        # previous render clear
        for widget in self.sched_scroll.inner.winfo_children():
            widget.destroy()

        headers = ["Shift"] + DAYS

        # Header row 
        for col, text in enumerate(headers):
            tk.Label(
                self.sched_scroll.inner, text=text,
                font=("Consolas", 10, "bold"),
                bg=BG_HEADER, fg=FG_HEADER,
                padx=10, pady=6, anchor="center", relief="flat"
            ).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        # Shift rows
        for r, shift in enumerate(ACTUAL_SHIFTS, start=1):
            bg_row = "#f2f2f2" if r % 2 == 0 else "#ffffff"

            # Shift name column
            tk.Label(
                self.sched_scroll.inner, text=shift.upper(),
                font=("Consolas", 10, "bold"),
                bg=bg_row, padx=10, pady=6, anchor="w", relief="flat"
            ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)

            # One cell per day
            for c, day in enumerate(DAYS, start=1):
                staff = schedule[day][shift]

                if len(staff) == 0:
                    txt, fg = "Unstaffed", STATUS_FAIL
                elif len(staff) == 1:
                    txt, fg = f"{staff[0]['name']}", STATUS_WARN
                else:
                    txt, fg = (f"{staff[0]['name']}, {staff[1]['name']}",
                               STATUS_OK)

                tk.Label(
                    self.sched_scroll.inner, text=txt,
                    font=("Consolas", 9), bg=bg_row, fg=fg,
                    padx=8, pady=5, anchor="w", relief="flat"
                ).grid(row=r, column=c, sticky="nsew", padx=1, pady=1)

        # Equal-width columns
        for col in range(len(headers)):
            self.sched_scroll.inner.grid_columnconfigure(col, weight=1)

        self.sched_scroll.refresh()




if __name__ == "__main__":
    root = tk.Tk()
    ShiftScheduler(root)
    root.mainloop()