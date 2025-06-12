import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import sys
from datetime import datetime
import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# IS 456:2000 Table 5 | "Exposure condition": [Minimum cement content in kg/m^3, Maximum water to cement ratio] 
is456_t5 = { "Mild": [300, 0.55], "Moderate": [300, 0.50], "Severe": [320, 0.45], "Very severe": [340, 0.45], "Extreme": [360, 0.40] }

# IS 10262:2009 Table 1 | "Grade": Assumed Standard Deviation
is10262_t1 = { "M1": 3.5, "M2": 4.0, "M3_5": 5.0 }

# IS 10262:2009 Table 2 | "Nominal Maximum Size Of Aggregate in mm": Maximum Water content in kg
is10262_t2 = { "10": 208, "20": 186, "40": 165 }

# IS 10262:2009 Table 3 | "Nominal Maximum Size Of Aggregate in mm": (vol of coarse aggregates)[Zone 4, Zone 3, Zone 2, Zone 1]
is10262_t3 = { "10": [0.50, 0.48, 0.46, 0.44], "20": [0.66, 0.64, 0.62, 0.60], "40": [0.75, 0.73, 0.71, 0.69] }

class MixDesignCalculator:
    def __init__(self, root):
        """Initialize the calculator"""
        self.root = root
        self.root.title("Advanced Concrete Mix Calculator")
        self.current_row = 0
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Create frames
        self.frame_left = ttk.Frame(self.root, padding=10)
        self.frame_left.grid(column=0, row=0, sticky=(tk.W, tk.N, tk.S))
        
        self.frame_right = ttk.Frame(self.root, padding=10)
        self.frame_right.grid(column=1, row=0, sticky=(tk.N, tk.S))
        
        # Initialize variables
        self.calculation_cache = {}
        self.mix_design_history = []
        
        # Load mix history
        self.load_mix_history()
        
        self.unit_system = tk.StringVar(value="Metric")  # Initialize unit system variable
        
        # Initialize widgets
        self.setup_input_validation()
        self.create_input_widgets()
        self.create_output_widgets()
        self.create_menu()

    def load_mix_history(self):
        """Load mix design history from file"""
        try:
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mix_history.json')
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.mix_design_history = json.load(f)
        except Exception as e:
            print(f"Failed to load mix history: {str(e)}")
            self.mix_design_history = []

    def save_mix_history(self):
        """Save mix design history to file"""
        try:
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mix_history.json')
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.mix_design_history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save mix history: {str(e)}")

    def update_mix_history(self, mix_data):
        """Update mix design history"""
        try:
            mix_entry = {
                "id": len(self.mix_design_history) + 1,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "grade": mix_data["Grade Designation"],
                "strength": float(mix_data.get("Target Strength", 0)),
                "wc_ratio": float(mix_data.get("Water Cement Ratio", 0)),
                "cement": float(mix_data.get("Cement Content", 0)),
                "water": float(mix_data.get("Water Content", 0)),
                "fine_agg": float(mix_data.get("Fine Aggregate", 0)),
                "coarse_agg": float(mix_data.get("Coarse Aggregate", 0)),
                "admixture": float(mix_data.get("Chemical Admixture", 0))
            }
            
            # Add fly ash data if present
            if mix_data.get("Fly Ash Content"):
                mix_entry.update({
                    "fly_ash": float(mix_data["Fly Ash Content"]),
                    "cement_saved": float(mix_data.get("Cement Saved", 0))
                })
            
            self.mix_design_history.append(mix_entry)
            self.save_mix_history()
            
        except Exception as e:
            print(f"Failed to update mix history: {str(e)}")

    def setup_input_validation(self):
        self.validators = {
            'float': (self.root.register(self.validate_float), '%P'),
            'grade': (self.root.register(self.validate_grade), '%P')
        }
    
    def validate_float(self, value):
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def validate_grade(self, value):
        """Validate grade input"""
        if value == "" or value == "M" or value == "M ":
            return True
        # Allow backspace/deletion
        if len(value) < len(self.grade_entry.get()):
            return True
        # Allow M followed by space and numbers
        if value.upper().startswith('M'):
            rest = value.replace('M', '').strip()
            return rest == "" or rest.isdigit()
        return False

    def create_input_widgets(self):
        # Grade Designation
        self.grade_label = ttk.Label(self.frame_left, text="Grade Designation:")
        self.grade_label.grid(row=self.current_row, column=0, sticky=tk.W)
        self.grade_entry = ttk.Entry(self.frame_left, width=23, validate="key", 
                                   validatecommand=self.validators['grade'])
        self.grade_entry.grid(row=self.current_row, column=1)
        self.grade_entry.insert(0, "M 25")
        self.current_row += 1

        # Mineral Admixture
        self.mineral_admixture_label = ttk.Label(self.frame_left, text="Mineral Admixture:")
        self.mineral_admixture_label.grid(row=self.current_row, column=0, sticky=tk.W)
        self.mineral_admixture_var = tk.StringVar(value="None")
        self.mineral_admixture_dropdown = ttk.Combobox(self.frame_left, 
                                                     textvariable=self.mineral_admixture_var,
                                                     values=["None", "Flyash"], width=20)
        self.mineral_admixture_dropdown.grid(row=self.current_row, column=1)
        self.current_row += 1

        # Nominal Size
        self.nominal_size_label = ttk.Label(self.frame_left, text="Nominal Size of Aggregate (mm):")
        self.nominal_size_label.grid(row=self.current_row, column=0, sticky=tk.W)
        self.nominal_size_entry = ttk.Entry(self.frame_left, width=23, validate="key",
                                          validatecommand=self.validators['float'])
        self.nominal_size_entry.grid(row=self.current_row, column=1)
        self.nominal_size_entry.insert(0, "20")
        self.current_row += 1

        # Workability
        self.workability_label = ttk.Label(self.frame_left, text="Workability (mm):")
        self.workability_label.grid(row=self.current_row, column=0, sticky=tk.W)
        self.workability_entry = ttk.Entry(self.frame_left, width=23, validate="key",
                                         validatecommand=self.validators['float'])
        self.workability_entry.grid(row=self.current_row, column=1)
        self.workability_entry.insert(0, "100")
        self.current_row += 1

        # Add all other input widgets with validation
        self.create_combobox("Exposure Conditions:", ["Mild", "Moderate", "Severe", "Very Severe", "Extreme"])
        self.create_combobox("Pump Concrete:", ["No", "Yes"])
        self.create_combobox("Type of Aggregate:", ["Sub-angular", "Gravel", "Rounded Gravel", "Crushed Angular"])
        self.create_combobox("Chemical Admixture:", ["Plasticizer", "Superplasticizer"])
        
        # Create specific gravity entries
        self.cement_sg_entry = self.create_validated_entry("Cement Specific Gravity", "3.15")
        self.coarse_agg_sg_entry = self.create_validated_entry("Coarse Aggregate Specific Gravity", "2.74")
        self.fine_agg_sg_entry = self.create_validated_entry("Fine Aggregate Specific Gravity", "2.74")
        self.chem_admixture_sg_entry = self.create_validated_entry("Chemical Admixture Specific Gravity", "1.145")
        
        # Create water absorption entries
        self.coarse_agg_water_absorption_entry = self.create_validated_entry("Coarse Aggregate Water Absorption Percent", "0.5")
        self.fine_agg_water_absorption_entry = self.create_validated_entry("Fine Aggregate Water Absorption Percent", "1.0")
        
        # Create zone and surface moisture entries
        self.create_combobox("Zone of Fine Aggregate:", ["Zone-I", "Zone-II", "Zone-III", "Zone-IV"])
        self.coarse_agg_surface_moisture_entry = self.create_validated_entry("Coarse Aggregate Surface Moisture Percent", "0")
        self.fine_agg_surface_moisture_entry = self.create_validated_entry("Fine Aggregate Surface Moisture Percent", "0")
        self.flyash_sg_entry = self.create_validated_entry("Fly Ash Specific Gravity", "2.2")

        # Calculate Button
        self.calculate_button = ttk.Button(self.frame_left, text="Calculate Mix Design", 
                                         command=self.calculate_concrete_mix)
        self.calculate_button.grid(row=self.current_row, column=0, columnspan=2, pady=10)

    def create_validated_entry(self, label_text, default_value):
        """Create a labeled entry with float validation"""
        label = ttk.Label(self.frame_left, text=label_text)
        label.grid(row=self.current_row, column=0, sticky=tk.W)
        
        # Create a reliable attribute name
        entry_name = label_text.lower().replace(' ', '_').replace(':', '').replace('(', '').replace(')', '').replace('%', 'percent') + '_entry'
        
        # Create and store the entry widget
        entry = ttk.Entry(self.frame_left, width=23, validate="key",
                         validatecommand=self.validators['float'])
        entry.grid(row=self.current_row, column=1)
        entry.insert(0, default_value)
        
        # Store the entry widget as an instance attribute
        setattr(self, entry_name, entry)
        
        self.current_row += 1
        return entry

    def create_combobox(self, label_text, values):
        """Create a labeled combobox"""
        label = ttk.Label(self.frame_left, text=label_text)
        label.grid(row=self.current_row, column=0, sticky=tk.W)
        
        # Create a more reliable variable name
        var_name = label_text.lower().replace(' ', '_').replace(':', '').replace('(', '').replace(')', '') + '_var'
        combo_name = label_text.lower().replace(' ', '_').replace(':', '').replace('(', '').replace(')', '') + '_dropdown'
        
        # Create and store the variable
        var = tk.StringVar(value=values[0])
        setattr(self, var_name, var)
        
        # Create and store the combobox
        combo = ttk.Combobox(self.frame_left, textvariable=var,
                            values=values, width=20, state="readonly")
        combo.grid(row=self.current_row, column=1)
        setattr(self, combo_name, combo)
        
        self.current_row += 1
        return combo, var

    def create_output_widgets(self):
        # Create notebook for results
        self.notebook = ttk.Notebook(self.frame_right)
        self.notebook.pack(fill='both', expand=True)
        
        # Mix Calculations tab
        mix_calc_frame = ttk.Frame(self.notebook)
        self.notebook.add(mix_calc_frame, text='Mix Calculations')
        self.volumes_text = self.create_result_text(mix_calc_frame, 
            "Mix Calculations per unit volume of Concrete:")
        
        # Mix Proportions tab
        mix_prop_frame = ttk.Frame(self.notebook)
        self.notebook.add(mix_prop_frame, text='Mix Proportions')
        self.trail_mix_text = self.create_result_text(mix_prop_frame,
            "Mix Proportions for this trial:")
        
        # Water Corrections tab
        water_corr_frame = ttk.Frame(self.notebook)
        self.notebook.add(water_corr_frame, text='Water Corrections')
        self.free_water_content_text = self.create_result_text(water_corr_frame,
            "Correction for Water absorption of aggregate:")
        
        # Final Results tab
        final_frame = ttk.Frame(self.notebook)
        self.notebook.add(final_frame, text='Final Results')
        self.final_data_text = self.create_result_text(final_frame,
            "Final data:")

    def create_result_text(self, parent, label_text):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        label = ttk.Label(frame, text=label_text)
        label.pack(anchor='w')
        
        text_widget = tk.Text(frame, height=15, width=50)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        return text_widget

    def target_strength_calculation(self, grade):
        """Target Strength for Mix Propotioning"""
        if grade == "M 10" or grade == "M 15":
            g = "M1"
        elif grade == "M 20" or grade == "M 25":
            g = "M2"
        else:
            g = "M3_5"
        
        for x, s in is10262_t1.items():
            if x == g:
                sd = s
        
        return int(grade.replace("M ",'')) + (1.65 * sd)

    def water_cement_ratio_calculation(self, exposure):
        """Selection Of Water Cement Ratio"""
        exp = exposure.capitalize()
        for x, v in is456_t5.items():
            if x == exp:
                wcr = v[1]
        return wcr

    def water_content_calculation(self, workability, nominal_size, aggregate_type, chemical_admixture):
        """Selection Of Water Content"""
        try:
            # Factor for conversion of water content of 50 mm slump to required slump
            n = (float(workability) - 50) / 25
            
            water_content = 0
            for x, v in is10262_t2.items():
                if x == str(nominal_size):
                    water_content = v
                    break
            
            if not water_content:
                raise ValueError(f"Invalid nominal size: {nominal_size}")
            
            # Convert aggregate type to lowercase for comparison
            agg_type = aggregate_type.lower()
            if "sub-angular" in agg_type:
                water_content -= 10
            elif "gravel" in agg_type:
                water_content -= 20
            elif "rounded gravel" in agg_type:
                water_content -= 25
            
            if float(workability) > 50:
                water_content += (0.03 * n * water_content)

            # Convert chemical admixture to lowercase for comparison
            chem_type = chemical_admixture.lower()
            if "superplasticizer" in chem_type:
                water_content -= water_content * 0.2
            elif "plasticizer" in chem_type:
                water_content -= water_content * 0.1

            return water_content
            
        except Exception as e:
            messagebox.showerror("Error", f"Water content calculation failed: {str(e)}")
            raise

    def cement_content_calculation(self, exposure_condition, WATER_CEMENT_RATIO, WATER_CONTENT):
        """Calculation Of Cement Content"""
        exp = exposure_condition.capitalize()
        for x, v in is456_t5.items():
            if x == exp:
                min_cc = v[0]
        
        cement_content = WATER_CONTENT/WATER_CEMENT_RATIO

        if cement_content < min_cc:
            cement_content = min_cc
        
        return cement_content

    def fly_cement_content_calculation(self, exposure_condition, WATER_CEMENT_RATIO, WATER_CONTENT):
        """Calculation Of Cement and Fly Ash Content"""
        exp = exposure_condition.capitalize()
        for x, v in is456_t5.items():
            if x == exp:
                min_cc = v[0]
        
        cement_content = WATER_CONTENT/WATER_CEMENT_RATIO
        temp1 = cement_content

        if cement_content < min_cc:
            cement_content = min_cc
            temp1 = cement_content

        cement_content *= 1.10

        new_water_cement_ratio = WATER_CONTENT/cement_content

        flyash_content = cement_content * 0.3

        temp2 = cement_content

        temp2 -= flyash_content

        if temp2 < 270:
            i = 0.25
            while True and i > 0:
                temp2 = cement_content
                flyash_content = temp2 * i
                temp2 -= flyash_content
                i -= 0.05
                if temp2 >= 270:
                    messagebox.showinfo("Alert", "Fly mix is possible!")
                    percent_flyash = int((i+0.05)*100)
                    break
                elif i < 0:
                    messagebox.showinfo("Alert", "Fly mix is not possible!")
                    break
        
        cement_content = temp2
        cement_saved = temp1 - cement_content

        return cement_content, flyash_content, cement_saved, new_water_cement_ratio, percent_flyash

    def vol_of_CAnFA_calculation(self, fine_agg_zone, nominal_size, WATER_CEMENT_RATIO, pump_concrete):
        """Proportion Of Volume Of Coarse Aggregate And Fine Aggregate Content"""
        if fine_agg_zone == "Zone-IV":
            i = 0
        elif fine_agg_zone == "Zone-III":
            i = 1
        elif fine_agg_zone == "Zone-II":
            i = 2
        elif fine_agg_zone == "Zone-I":
            i = 3
        
        for x, v in is10262_t3.items():
            if x == nominal_size:
                vol_CA = v[i]
        
        if WATER_CEMENT_RATIO > 0.5:
            vol_CA -= 0.01*((WATER_CEMENT_RATIO - 0.5)/0.05)
        else:
            vol_CA += 0.01*((0.5 - WATER_CEMENT_RATIO)/0.05)

        if pump_concrete == "Yes":
            vol_CA *= 0.9

        vol_FA = 1 - vol_CA

        return vol_CA, vol_FA

    def mix_calculation(self, cc, sp_c, wc, v_ca, v_fa, sp_ca, sp_fa, sp_chemad):
        """Mix Calculations per unit volume of concrete"""
        # Volume of cement
        vol_cement = (cc/sp_c) * 0.001

        # Volume of water
        vol_water = wc * 0.001

        # Volume of Chemical Admixture @ 2% by cementitious material
        mass_of_chemAd = cc * 0.02
        vol_chemAd = (mass_of_chemAd / sp_chemad) * 0.001

        # Volume of all in aggregate
        vol_all_aggr = (1 - (vol_cement + vol_water + vol_chemAd))

        # Mass of Coarse aggregate
        mass_CA = vol_all_aggr * v_ca * sp_ca * 1000

        # Mass of Fine aggregate
        mass_FA = vol_all_aggr * v_fa * sp_fa * 1000

        return mass_of_chemAd, mass_CA, mass_FA, vol_cement, vol_water, vol_all_aggr, vol_chemAd

    def fly_mix_calculation(self, cc, sp_c, wc, v_ca, v_fa, sp_ca, sp_fa, sp_fly, sp_chemad, fc):
        """Mix Calculations per unit volume of concrete"""
        # Volume of cement
        vol_cement = (cc/sp_c) * 0.001

        # Volume of fly ash
        vol_flyash = (fc/sp_fly) * 0.001

        # Volume of water
        vol_water = wc * 0.001

        # Volume of Chemical Admixture @ 2% by cementitious material
        mass_of_chemAd = cc * 0.02
        vol_chemAd = (mass_of_chemAd / sp_chemad) * 0.001

        # Volume of all in aggregate
        vol_all_aggr = (1 - (vol_cement + vol_flyash + vol_water + vol_chemAd))

        # Mass of Coarse aggregate
        mass_CA = vol_all_aggr * v_ca * sp_ca * 1000

        # Mass of Fine aggregate
        mass_FA = vol_all_aggr * v_fa * sp_fa * 1000

        return mass_of_chemAd, mass_CA, mass_FA, vol_cement, vol_flyash, vol_water, vol_chemAd, vol_all_aggr

    def calculate_concrete_mix(self):
        try:
            # Get input values
            grade_designation = self.grade_entry.get().upper()
            if len(grade_designation) == 3:
                grade_designation = grade_designation.replace('M','M ')

            mineral_admixture = self.mineral_admixture_var.get()
            nominal_size = self.nominal_size_entry.get()
            workability = self.workability_entry.get()
            exposure_condition = self.exposure_conditions_var.get()
            pump_concrete = self.pump_concrete_var.get()
            aggregate_type = self.type_of_aggregate_var.get()
            chemical_admixture = self.chemical_admixture_var.get()
            
            # Get values from entries
            cement_sg = float(self.cement_sg_entry.get())
            coarse_agg_sg = float(self.coarse_agg_sg_entry.get())
            fine_agg_sg = float(self.fine_agg_sg_entry.get())
            chem_admixture_sg = float(self.chem_admixture_sg_entry.get())
            coarse_agg_water_absorption = float(self.coarse_agg_water_absorption_entry.get())
            fine_agg_water_absorption = float(self.fine_agg_water_absorption_entry.get())
            fine_agg_zone = self.zone_of_fine_aggregate_var.get()
            coarse_agg_surface_moisture = float(self.coarse_agg_surface_moisture_entry.get())
            fine_agg_surface_moisture = float(self.fine_agg_surface_moisture_entry.get())
            flyash_sg = float(self.flyash_sg_entry.get())

            # Validate required inputs
            if not all([grade_designation, nominal_size, workability, exposure_condition, 
                       aggregate_type, chemical_admixture]):
                raise ValueError("All required fields must be filled")

            # Cache key for results
            cache_key = f"{grade_designation}_{mineral_admixture}_{nominal_size}_{workability}_{exposure_condition}"
            
            if cache_key in self.calculation_cache:
                self.display_results(self.calculation_cache[cache_key])
                return

            # Calculations
            TARGET_STRENGTH = self.target_strength_calculation(grade_designation)
            WATER_CEMENT_RATIO = self.water_cement_ratio_calculation(exposure_condition)
            WATER_CONTENT = self.water_content_calculation(workability, nominal_size, aggregate_type, chemical_admixture)

            # Store calculation data for history
            calc_data = {
                "Grade Designation": grade_designation,
                "Target Strength": TARGET_STRENGTH,
                "Water Cement Ratio": WATER_CEMENT_RATIO,
                "Water Content": WATER_CONTENT,
                "Exposure Condition": exposure_condition,
                "Mineral Admixture": mineral_admixture
            }

            if mineral_admixture == "None":
                CEMENT_CONTENT = self.cement_content_calculation(exposure_condition, WATER_CEMENT_RATIO, WATER_CONTENT)
                VOL_CA, VOL_FA = self.vol_of_CAnFA_calculation(fine_agg_zone, nominal_size, WATER_CEMENT_RATIO, pump_concrete)

                MASS_CHEM_AD, MASS_CA, MASS_FA, vol_cement, vol_water, vol_all_aggr, vol_chemAd = self.mix_calculation(
                    CEMENT_CONTENT, cement_sg, WATER_CONTENT, VOL_CA, VOL_FA, 
                    coarse_agg_sg, fine_agg_sg, chem_admixture_sg
                )

                # Water absorption correction
                CA_WA = MASS_CA * coarse_agg_water_absorption * 0.01
                FA_WA = MASS_FA * fine_agg_water_absorption * 0.01

                # Surface Moisture Correction
                CA_SM = MASS_CA * coarse_agg_surface_moisture * 0.01
                FA_SM = MASS_FA * fine_agg_surface_moisture * 0.01

                # Update calculation data
                calc_data.update({
                    "Cement Content": CEMENT_CONTENT,
                    "Fine Aggregate": MASS_FA,
                    "Coarse Aggregate": MASS_CA,
                    "Chemical Admixture": MASS_CHEM_AD,
                    "Water Correction": WATER_CONTENT + CA_WA + FA_WA - CA_SM - FA_SM
                })

                # Validate cement content before division
                if CEMENT_CONTENT <= 0:
                    raise ValueError("Invalid cement content: must be greater than 0")

                # Prepare results
                results = {
                    'volumes_result': (
                        f"1. Volume of Cement                  : {round(vol_cement,3)} m^3\n"
                        f"2. Volume of Water                   : {round(vol_water,3)} m^3\n"
                        f"3. Proportion of Volume of C.A       : {round(VOL_CA,3)}\n"
                        f"4. Proportion of Volume of F.A       : {round(VOL_FA,3)}\n"
                        f"5. Volume of All in Aggregate        : {round(vol_all_aggr,3)} m^3\n"
                        f"6. Volume of Chemical Admixture      : {round(vol_chemAd,3)} m^3\n"
                    ),
                    'trail_mix_result': (
                        f"1. Target Strength      : {round(TARGET_STRENGTH,3)} MPa\n"
                        f"2. Water Cement Ratio   : {round(WATER_CEMENT_RATIO,3)}\n"
                        f"3. Cement               : {round(CEMENT_CONTENT, 3)} kg/m^3\n"
                        f"4. Water                : {round(WATER_CONTENT, 3)} Lit\n"
                        f"5. Fine Aggregate       : {round(MASS_FA,3)} kg\n"
                        f"6. Coarse Aggregate     : {round(MASS_CA,3)} kg\n"
                        f"7. Chemical Admixture   : {round(MASS_CHEM_AD,3)} kg/m^3\n"
                    ),
                    'free_water_content_result': (
                        f"1. Correction for water absorption of aggregate:\n"
                        f"\ta. Coarse aggregate  :{round(CA_WA,3)} Lit\n"
                        f"\tb. Fine aggregate    :{round(FA_WA,3)} Lit\n"
                        f"2. Correction for Surface Moisture of aggregate:\n"
                        f"\ta. Coarse aggregate  :{round(CA_SM,3)} Lit\n"
                        f"\tb. Fine aggregate    :{round(FA_SM,3)} Lit\n"
                    ),
                    'final_data_result': (
                        f"1. Water content after correction is : {round((WATER_CONTENT + CA_WA + FA_WA - CA_SM - FA_SM),3)} Lit\n"
                        f"2. Mix Proportion by weights:\n"
                        f"3. C : F.A : C.A : W = {round(CEMENT_CONTENT/CEMENT_CONTENT,2)} : {round(MASS_FA/CEMENT_CONTENT,2)}: {round(MASS_CA/CEMENT_CONTENT,2)} : {round((WATER_CONTENT + CA_WA + FA_WA - CA_SM - FA_SM)/CEMENT_CONTENT,2)}\n"
                        f"4. Units required as per a cement bag: \n"
                        f"\ta. Cement                :{round(CEMENT_CONTENT/50,1)}\n"
                        f"\tb. Fine Aggregate        :{round(MASS_FA/50,1)}\n"
                        f"\tc. Coarse Aggregate      :{round(MASS_CA/50,1)}\n"
                    )
                }
            else:  # Flyash calculations
                CEMENT_CONTENT, FLYASH_CONTENT, CEMENT_SAVED, NEW_WATER_CEMENT_RATIO, percent_flyash = self.fly_cement_content_calculation(
                    exposure_condition, WATER_CEMENT_RATIO, WATER_CONTENT
                )
                
                VOL_CA, VOL_FA = self.vol_of_CAnFA_calculation(fine_agg_zone, nominal_size, WATER_CEMENT_RATIO, pump_concrete)

                MASS_CHEM_AD, MASS_CA, MASS_FA, vol_cement, vol_flyash, vol_water, vol_chemAd, vol_all_aggr = self.fly_mix_calculation(
                    CEMENT_CONTENT, cement_sg, WATER_CONTENT, VOL_CA, VOL_FA,
                    coarse_agg_sg, fine_agg_sg, flyash_sg, chem_admixture_sg, FLYASH_CONTENT
                )

                # Water absorption correction
                CA_WA = MASS_CA * coarse_agg_water_absorption * 0.01
                FA_WA = MASS_FA * fine_agg_water_absorption * 0.01

                # Surface Moisture Correction
                CA_SM = MASS_CA * coarse_agg_surface_moisture * 0.01
                FA_SM = MASS_FA * fine_agg_surface_moisture * 0.01

                # Update calculation data
                calc_data.update({
                    "Cement Content": CEMENT_CONTENT,
                    "Fly Ash Content": FLYASH_CONTENT,
                    "Cement Saved": CEMENT_SAVED,
                    "New Water Cement Ratio": NEW_WATER_CEMENT_RATIO,
                    "Fine Aggregate": MASS_FA,
                    "Coarse Aggregate": MASS_CA,
                    "Chemical Admixture": MASS_CHEM_AD,
                    "Water Correction": WATER_CONTENT + CA_WA + FA_WA - CA_SM - FA_SM
                })

                # Validate cement content before division
                if CEMENT_CONTENT <= 0:
                    raise ValueError("Invalid cement content: must be greater than 0")

                # Prepare results
                results = {
                    'volumes_result': (
                        f"1. Volume of Cement                  : {round(vol_cement,3)} m^3\n"
                        f"2. Percentage of Fly Ash             : {round(percent_flyash,3)} %\n"
                        f"3. Volume of Fly Ash                 : {round(vol_flyash,3)} m^3\n"
                        f"4. Volume of Water                   : {round(vol_water,3)} m^3\n"
                        f"5. Proportion of Volume of C.A       : {round(VOL_CA,3)}\n"
                        f"6. Proportion of Volume of F.A       : {round(VOL_FA,3)}\n"
                        f"7. Volume of All in Aggregate        : {round(vol_all_aggr,3)} m^3\n"
                        f"8. Volume of Chemical Admixture      : {round(vol_chemAd,3)} m^3\n"
                    ),
                    'trail_mix_result': (
                        f"1. Target Strength         : {round(TARGET_STRENGTH,3)} MPa\n"
                        f"2. Fly Ash                 : {round(FLYASH_CONTENT,3)} kg/m^3\n"
                        f"3. Water Cement Ratio      : {round(NEW_WATER_CEMENT_RATIO,3)}\n"
                        f"4. Cement                  : {round(CEMENT_CONTENT,3)} kg/m^3\n"
                        f"5. Water                   : {round(WATER_CONTENT,3)} Lit\n"
                        f"6. Fine Aggregate          : {round(MASS_FA,3)} kg\n"
                        f"7. Coarse Aggregate        : {round(MASS_CA,3)} kg\n"
                        f"8. Chemical Admixture      : {round(MASS_CHEM_AD,3)} kg/m^3\n"
                    ),
                    'free_water_content_result': (
                        f"1. Correction for water absorption of aggregate:\n"
                        f"\ta. Coarse aggregate  :{round(CA_WA,3)} Lit\n"
                        f"\tb. Fine aggregate    :{round(FA_WA,3)} Lit\n"
                        f"2. Correction for Surface Moisture of aggregate:\n"
                        f"\ta. Coarse aggregate  :{round(CA_SM,3)} Lit\n"
                        f"\tb. Fine aggregate    :{round(FA_SM,3)} Lit\n"
                    ),
                    'final_data_result': (
                        f"1. Water content after correction is : {round((WATER_CONTENT + CA_WA + FA_WA - CA_SM - FA_SM),3)} Lit\n"
                        f"2. Cement saved                      : {round(CEMENT_SAVED,3)} kg/m^3\n"
                        f"3. Mix Proportion by weights:\n"
                        f"4. C : FA : F.A : C.A : W = {round(CEMENT_CONTENT/CEMENT_CONTENT,2)} : {round(FLYASH_CONTENT/CEMENT_CONTENT,2)} : {round(MASS_FA/CEMENT_CONTENT,2)} : {round(MASS_CA/CEMENT_CONTENT,2)} : {round((WATER_CONTENT + CA_WA + FA_WA - CA_SM - FA_SM)/CEMENT_CONTENT,2)}\n"
                        f"5. Units required as per a cement bag: \n"
                        f"\ta. Cement                :{round(CEMENT_CONTENT/50,1)}\n"
                        f"\tb. Fly Ash               :{round(FLYASH_CONTENT/50,1)}\n"
                        f"\tc. Fine Aggregate        :{round(MASS_FA/50,1)}\n"
                        f"\td. Coarse Aggregate      :{round(MASS_CA/50,1)}\n"
                    )
                }

            # Cache the results and update history
            self.calculation_cache[cache_key] = results
            self.current_results = results
            self.update_mix_history(calc_data)
            
            # Display results
            self.display_results(results)
            messagebox.showinfo("Success", "Calculation completed successfully!")
            
        except ValueError as ve:
            messagebox.showerror("Input Error", str(ve))
        except Exception as e:
            messagebox.showerror("Calculation Error", f"An error occurred: {str(e)}")
            raise  # Re-raise for debugging

    def display_results(self, results):
        # Clear previous results
        self.volumes_text.delete(1.0, tk.END)
        self.trail_mix_text.delete(1.0, tk.END)
        self.free_water_content_text.delete(1.0, tk.END)
        self.final_data_text.delete(1.0, tk.END)
        
        # Display new results
        self.volumes_text.insert(tk.END, results['volumes_result'])
        self.trail_mix_text.insert(tk.END, results['trail_mix_result'])
        self.free_water_content_text.insert(tk.END, results['free_water_content_result'])
        self.final_data_text.insert(tk.END, results['final_data_result'])

    def create_menu(self):
        """Create menu bar with File and Tools options"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Mix Design", command=self.save_mix_design)
        file_menu.add_command(label="Load Mix Design", command=self.load_mix_design)
        file_menu.add_separator()
        file_menu.add_command(label="Export to PDF", command=self.export_to_pdf)
        file_menu.add_command(label="Export to Excel", command=self.export_to_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Show Save Locations", command=self.show_save_locations)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Strength Predictor", command=self.show_strength_predictor)
        tools_menu.add_command(label="Batch Calculator", command=self.show_batch_calculator)
        tools_menu.add_command(label="Cost Calculator", command=self.show_cost_calculator)
        tools_menu.add_command(label="Temperature Effects", command=self.show_temperature_calculator)
        tools_menu.add_separator()
        tools_menu.add_command(label="Mix Design History", command=self.show_mix_history)
        tools_menu.add_command(label="Compare Mix Designs", command=self.show_mix_comparison)
        
        # Units Menu
        units_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Units", menu=units_menu)
        units_menu.add_radiobutton(label="Metric", variable=self.unit_system,
                                 command=lambda: self.change_unit_system("Metric"))
        units_menu.add_radiobutton(label="Imperial", variable=self.unit_system,
                                 command=lambda: self.change_unit_system("Imperial"))

    def show_strength_predictor(self):
        """Show strength predictor window using ML model"""
        try:
            import pandas as pd
            import numpy as np
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import seaborn as sns
            import joblib
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            import mplcursors

            predictor_window = tk.Toplevel(self.root)
            predictor_window.title("Concrete Strength Predictor")
            predictor_window.geometry("1200x1000")  # Increased height for heatmap

            # Create main frames
            main_frame = ttk.Frame(predictor_window)
            main_frame.pack(expand=True, fill="both")

            input_frame = ttk.Frame(main_frame, padding=10, style='Input.TFrame')
            input_frame.pack(side="left", fill="both", padx=10, pady=10)

            output_frame = ttk.Frame(main_frame, padding=10, style='Output.TFrame')
            output_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

            # Input fields
            labels = [
                'Cement (Kg/m³)', 
                'Blast Furnace Slag (Kg/m³)', 
                'Fly Ash (Kg/m³)', 
                'Water (Liters)',
                'Superplasticizer (Kg/m³)', 
                'Coarse Aggregate (Kg/m³)', 
                'Fine Aggregate (Kg/m³)', 
                'Age (days)'
            ]
            entries = []

            # Create input fields
            for i, label in enumerate(labels):
                ttk.Label(input_frame, text=label).grid(row=i, column=0, sticky='w', pady=5)
                if label == 'Age (days)':
                    age_var = tk.StringVar()
                    age_dropdown = ttk.Combobox(input_frame, textvariable=age_var, 
                                              values=[7, 14, 28, 56, 90, 180, 360], 
                                              state='readonly', width=20)
                    age_dropdown.grid(row=i, column=1, pady=5)
                    age_dropdown.set(28)  # Default age
                    entries.append(age_dropdown)
                else:
                    entry = ttk.Entry(input_frame, width=20, validate="key", 
                                    validatecommand=self.validators['float'])
                    entry.grid(row=i, column=1, sticky='w', pady=5)
                    entries.append(entry)

            # Result display
            result_frame = ttk.LabelFrame(output_frame, text="Prediction Results", padding=10)
            result_frame.pack(fill="x", padx=5, pady=5)

            result_text = tk.Text(result_frame, height=8, width=60)
            result_text.pack(pady=5)

            # Create main frame for visualization
            graph_frame = ttk.LabelFrame(output_frame, text="Prediction Visualization", padding=10)
            graph_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Create frame for plots
            plot_frame = ttk.Frame(graph_frame)
            plot_frame.pack(fill="both", expand=True)

            # Function to predict strength
            def predict_strength():
                try:
                    # Get input values
                    input_values = []
                    for entry in entries:
                        val = entry.get()
                        if not val:
                            raise ValueError("All fields must be filled!")
                        input_values.append(float(val))

                    # Load model and scaler
                    model = joblib.load('concrete_model.pkl')
                    scaler = joblib.load('concrete_scaler.pkl')

                    # Compute derived features
                    water_cement_ratio = input_values[3] / input_values[0]  # water / cement
                    total_binder = input_values[0] + input_values[1] + input_values[2]  # cement + slag + fly ash
                    log_age = np.log1p(input_values[7])  # log(age)
                    
                    # Create input array with derived features
                    input_features = input_values + [water_cement_ratio, total_binder, log_age]
                    input_array = np.array(input_features).reshape(1, -1)
                    
                    # Scale features
                    input_scaled = scaler.transform(input_array)
                    
                    # Make prediction
                    prediction = model.predict(input_scaled)[0]

                    # Display results
                    result_text.delete('1.0', tk.END)
                    result_text.insert(tk.END, f"🔵 Predicted Strength: {prediction:.2f} MPa\n\n")
                    result_text.insert(tk.END, "Mix Design Analysis:\n")
                    result_text.insert(tk.END, f"• Water-Cement Ratio: {water_cement_ratio:.3f}\n")
                    result_text.insert(tk.END, f"• Total Binder Content: {total_binder:.1f} kg/m³\n")
                    
                    # Strength classification
                    if prediction < 20:
                        strength_class = "Low Strength Concrete"
                    elif prediction < 35:
                        strength_class = "Normal Strength Concrete"
                    else:
                        strength_class = "High Strength Concrete"
                    
                    result_text.insert(tk.END, f"• Strength Classification: {strength_class}\n")
                    
                    # Plot prediction vs typical range
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 7), gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.3})
                    
                    # Upper plot - Prediction vs Expected
                    typical_range = np.arange(0, 80, 5)
                    ax1.plot(typical_range, typical_range, 'k--', label='Expected')
                    ax1.fill_between(typical_range, typical_range * 0.85, typical_range * 1.15, 
                                  alpha=0.2, color='gray', label='±15%')
                    ax1.scatter([prediction], [prediction], color='red', s=60, 
                             label='Prediction', zorder=5)
                    
                    ax1.set_xlabel('Design Strength (MPa)', fontsize=8)
                    ax1.set_ylabel('Predicted Strength (MPa)', fontsize=8)
                    ax1.set_title('Strength Analysis', fontsize=9, pad=5)
                    ax1.grid(True, alpha=0.2)
                    ax1.legend(fontsize=7, loc='upper left')
                    ax1.tick_params(labelsize=7)

                    # Lower plot - Heat Map
                    # Create correlation matrix from input parameters
                    param_names = ['Cement', 'Slag', 'Fly Ash', 'Water', 'SP', 'Coarse Agg', 'Fine Agg', 'Age', 'Strength']
                    correlation_data = np.array(input_values + [prediction]).reshape(1, -1)
                    correlation_matrix = np.corrcoef(correlation_data.T)
                    
                    # Create heatmap with adjusted font sizes
                    sns.heatmap(correlation_matrix, 
                               xticklabels=param_names,
                               yticklabels=param_names,
                               annot=True,
                               fmt='.2f',
                               cmap='coolwarm',
                               center=0,
                               ax=ax2,
                               annot_kws={'size': 6},
                               cbar_kws={'shrink': 0.7})
                    
                    # Adjust heatmap appearance
                    ax2.set_title('Parameter Correlation Heatmap', fontsize=9, pad=5)
                    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right', fontsize=7)
                    ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0, fontsize=7)
                    
                    # Adjust layout to prevent label cutoff
                    # Adjust subplot parameters for better layout
                    plt.subplots_adjust(left=0.15, right=0.9, top=0.9, bottom=0.1, hspace=0.4)

                    # Update graph
                    for widget in plot_frame.winfo_children():
                        widget.destroy()
                    
                    # Create matplotlib canvas
                    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
                    canvas.draw()
                    canvas_widget = canvas.get_tk_widget()
                    canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)
                    
                    plt.close(fig)  # Close the figure to free memory

                except Exception as e:
                    messagebox.showerror("Prediction Error", str(e))

            # Add predict button
            predict_btn = ttk.Button(input_frame, text="Predict Strength", 
                                   command=predict_strength)
            predict_btn.grid(row=len(labels), column=0, columnspan=2, pady=20)

            # Add help button
            def show_help():
                help_text = """Concrete Strength Predictor Help:

1. Input Guidelines:
   - Enter all values in the specified units
   - Age should be selected from the dropdown
   - All fields must be filled

2. Typical Ranges:
   - Cement: 200-550 kg/m³
   - Water: 150-200 L
   - Aggregates: 600-1200 kg/m³
   - Age: Select from dropdown

3. Notes:
   - The prediction model uses machine learning
   - Results include a ±15% confidence range
   - The graph shows prediction vs typical range
   - Heatmap shows parameter correlations"""
                
                messagebox.showinfo("Help", help_text)

            help_btn = ttk.Button(input_frame, text="Help", command=show_help)
            help_btn.grid(row=len(labels)+1, column=0, columnspan=2, pady=5)

            # Add initial heatmap
            heatmap_frame = ttk.LabelFrame(input_frame, text="Parameter Correlation Guide", padding=10)
            heatmap_frame.grid(row=len(labels)+2, column=0, columnspan=2, pady=10, sticky='ew')

            # Create and display initial heatmap
            fig_init, ax_init = plt.subplots(figsize=(6, 5))
            initial_correlations = np.array([
                [1.00, 0.30, 0.25, -0.40, 0.15, -0.10, -0.15, 0.35, 0.50],
                [0.30, 1.00, -0.30, -0.20, 0.20, -0.15, -0.10, 0.25, 0.45],
                [0.25, -0.30, 1.00, -0.15, 0.25, -0.05, -0.10, 0.20, 0.40],
                [-0.40, -0.20, -0.15, 1.00, -0.10, 0.05, 0.10, -0.30, -0.55],
                [0.15, 0.20, 0.25, -0.10, 1.00, -0.05, -0.05, 0.15, 0.25],
                [-0.10, -0.15, -0.05, 0.05, -0.05, 1.00, -0.60, -0.10, -0.15],
                [-0.15, -0.10, -0.10, 0.10, -0.05, -0.60, 1.00, -0.05, -0.10],
                [0.35, 0.25, 0.20, -0.30, 0.15, -0.10, -0.05, 1.00, 0.45],
                [0.50, 0.45, 0.40, -0.55, 0.25, -0.15, -0.10, 0.45, 1.00]
            ])

            param_names = ['Cement', 'Slag', 'Fly Ash', 'Water', 'SP', 'Coarse', 'Fine', 'Age', 'Strength']
            sns.heatmap(initial_correlations,
                       xticklabels=param_names,
                       yticklabels=param_names,
                       annot=True,
                       fmt='.2f',
                       cmap='coolwarm',
                       center=0,
                       ax=ax_init)
            ax_init.set_title('Typical Parameter Correlations')
            plt.xticks(rotation=45)
            plt.tight_layout()

            canvas_init = FigureCanvasTkAgg(fig_init, master=heatmap_frame)
            canvas_init.draw()
            canvas_init.get_tk_widget().pack(fill="both", expand=True)
            plt.close(fig_init)

            # Add explanation text
            explanation_text = tk.Text(heatmap_frame, height=4, width=40)
            explanation_text.pack(pady=5)
            explanation_text.insert(tk.END, 
                "The heatmap shows typical correlations between parameters and strength.\n"
                "• Red indicates positive correlation (parameters increase together)\n"
                "• Blue indicates negative correlation (one increases as other decreases)\n"
                "• Darker colors indicate stronger correlations")
            explanation_text.config(state='disabled')

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load strength predictor: {str(e)}")

    def save_mix_design(self):
        """Save current mix design to a JSON file"""
        try:
            if not hasattr(self, 'current_results'):
                messagebox.showerror("Error", "No mix design to save. Please calculate first.")
                return

            # Get save directory and ensure it exists
            base_dir = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.join(base_dir, 'saved_designs')
            os.makedirs(save_dir, exist_ok=True)
                
            data = {
                "inputs": self.get_current_mix_data(),
                "results": self.current_results,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            try:
                default_name = f"mix_design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # Force the save dialog to open in the saved_designs directory
                filename = filedialog.asksaveasfilename(
                    initialdir=save_dir,
                    initialfile=default_name,
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    parent=self.root
                )
                
                if filename:
                    try:
                        # Ensure the file will be saved in saved_designs directory
                        final_path = os.path.join(save_dir, os.path.basename(filename))
                        
                        # Check if file exists
                        if os.path.exists(final_path):
                            if not messagebox.askyesno("Confirm Overwrite", 
                                f"File {os.path.basename(final_path)} already exists.\nDo you want to overwrite it?"):
                                return

                        # Save the file in the saved_designs directory
                        with open(final_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                        
                        messagebox.showinfo("Success", 
                            f"Mix design saved successfully!\nLocation: {final_path}")
                        
                    except PermissionError:
                        messagebox.showerror("Permission Error", 
                            "Cannot write to file. Please check your permissions.")
                    except Exception as e:
                        print(f"Save error details: {str(e)}")
                        messagebox.showerror("Save Error", "Failed to save file. Please try again.")
                        
            except Exception as e:
                print(f"File dialog error: {str(e)}")
                messagebox.showerror("Error", "Failed to open save dialog")
                
        except Exception as e:
            print(f"Save error details: {str(e)}")
            messagebox.showerror("Error", "Unexpected error during save operation.")

    def export_to_pdf(self):
        """Export current mix design results to PDF"""
        if not hasattr(self, 'current_results'):
            messagebox.showerror("Error", "No results to export. Please calculate first.")
            return
            
        try:
            # Get export directory and ensure it exists
            base_dir = os.path.dirname(os.path.abspath(__file__))
            export_dir = os.path.join(base_dir, 'exports')
            os.makedirs(export_dir, exist_ok=True)

            try:
                default_name = f"mix_design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                
                filename = filedialog.asksaveasfilename(
                    initialdir=export_dir,
                    initialfile=default_name,
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    parent=self.root
                )
                
                if filename:
                    try:
                        # Ensure the file will be saved in exports directory
                        final_path = os.path.join(export_dir, os.path.basename(filename))
                        
                        # Check if file exists
                        if os.path.exists(final_path):
                            if not messagebox.askyesno("Confirm Overwrite", 
                                f"File {os.path.basename(final_path)} already exists.\nDo you want to overwrite it?"):
                                return

                        # Create the PDF document
                        doc = SimpleDocTemplate(
                            final_path,
                            pagesize=A4,
                            rightMargin=72,
                            leftMargin=72,
                            topMargin=72,
                            bottomMargin=72
                        )

                        # Create the content
                        styles = getSampleStyleSheet()
                        elements = []

                        # Add title
                        title_style = ParagraphStyle(
                            'CustomTitle',
                            parent=styles['Title'],
                            fontSize=24,
                            spaceAfter=30
                        )
                        elements.append(Paragraph("Concrete Mix Design Report", title_style))
                        elements.append(Spacer(1, 12))

                        # Add date
                        date_style = ParagraphStyle(
                            'Date',
                            parent=styles['Normal'],
                            fontSize=12,
                            spaceAfter=20
                        )
                        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", date_style))
                        elements.append(Spacer(1, 20))

                        # Add input parameters
                        elements.append(Paragraph("Input Parameters", styles['Heading1']))
                        input_data = self.get_current_mix_data()
                        input_table_data = [[Paragraph("Parameter", styles['Heading2']), 
                                           Paragraph("Value", styles['Heading2'])]]
                        for key, value in input_data.items():
                            input_table_data.append([Paragraph(str(key), styles['Normal']), 
                                                   Paragraph(str(value), styles['Normal'])])
                        
                        input_table = Table(input_table_data, colWidths=[250, 200])
                        input_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 14),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 12),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(input_table)
                        elements.append(Spacer(1, 20))

                        # Add results
                        elements.append(Paragraph("Results", styles['Heading1']))
                        for section, content in self.current_results.items():
                            section_title = section.replace('_result', '').replace('_', ' ').title()
                            elements.append(Paragraph(section_title, styles['Heading2']))
                            elements.append(Spacer(1, 12))
                            
                            # Split content into lines and create table data
                            lines = content.strip().split('\n')
                            table_data = []
                            for line in lines:
                                if line.strip():
                                    if line.startswith('\t'):
                                        table_data.append(['', Paragraph(line.strip(), styles['Normal'])])
                                    else:
                                        table_data.append([Paragraph(line.strip(), styles['Normal'])])
                            
                            if table_data:
                                result_table = Table(table_data, colWidths=[400])
                                result_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                                    ('FONTSIZE', (0, 0), (-1, -1), 12),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                                ]))
                                elements.append(result_table)
                            elements.append(Spacer(1, 12))

                        # Build the PDF
                        doc.build(elements)
                        
                        messagebox.showinfo("Success", 
                            f"Results exported to PDF successfully!\nLocation: {final_path}")
                        
                    except PermissionError:
                        messagebox.showerror("Permission Error", 
                            "Cannot write to file. Please check your permissions.")
                    except Exception as e:
                        print(f"PDF generation error: {str(e)}")
                        messagebox.showerror("Export Error", 
                            "Failed to generate PDF file. Please try again.")
                        
            except Exception as e:
                print(f"File dialog error: {str(e)}")
                messagebox.showerror("Error", "Failed to open save dialog")
                
        except Exception as e:
            print(f"PDF export error: {str(e)}")
            messagebox.showerror("Error", "Unexpected error during PDF export.")

    def get_current_mix_data(self):
        """Get current mix design input parameters"""
        return {
            "Grade Designation": self.grade_entry.get(),
            "Mineral Admixture": self.mineral_admixture_var.get(),
            "Nominal Size": self.nominal_size_entry.get(),
            "Workability": self.workability_entry.get(),
            "Exposure Condition": self.exposure_conditions_var.get(),
            "Pump Concrete": self.pump_concrete_var.get(),
            "Aggregate Type": self.type_of_aggregate_var.get(),
            "Chemical Admixture": self.chemical_admixture_var.get(),
            "Cement SG": self.cement_sg_entry.get(),
            "Coarse Aggregate SG": self.coarse_agg_sg_entry.get(),
            "Fine Aggregate SG": self.fine_agg_sg_entry.get(),
            "Chemical Admixture SG": self.chem_admixture_sg_entry.get(),
            "Coarse Aggregate Water Absorption": self.coarse_agg_water_absorption_entry.get(),
            "Fine Aggregate Water Absorption": self.fine_agg_water_absorption_entry.get(),
            "Fine Aggregate Zone": self.zone_of_fine_aggregate_var.get(),
            "Coarse Aggregate Surface Moisture": self.coarse_agg_surface_moisture_entry.get(),
            "Fine Aggregate Surface Moisture": self.fine_agg_surface_moisture_entry.get(),
            "Fly Ash SG": self.flyash_sg_entry.get()
        }

    def load_mix_design(self):
        """Load mix design from a JSON file"""
        try:
            # Get save directory and ensure it exists
            base_dir = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.join(base_dir, 'saved_designs')
            os.makedirs(save_dir, exist_ok=True)

            try:
                filename = filedialog.askopenfilename(
                    initialdir=save_dir,
                    title="Select Mix Design File",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    parent=self.root
                )
                
                if not filename:  # User cancelled
                    return
                
                # Ensure we're loading from saved_designs directory
                if not os.path.dirname(filename) == save_dir:
                    final_path = os.path.join(save_dir, os.path.basename(filename))
                    if not os.path.exists(final_path):
                        messagebox.showerror("Error", "Please select a file from the saved_designs folder")
                        return
                    filename = final_path
                
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Validate the loaded data
                    required_keys = ["inputs", "results"]
                    if not all(key in data for key in required_keys):
                        messagebox.showerror("Error", "Invalid mix design file format")
                        return
                    
                    # Load the data into the interface
                    self.load_mix_data(data["inputs"])
                    self.current_results = data["results"]
                    self.display_results(self.current_results)
                    
                    messagebox.showinfo("Success", f"Mix design loaded successfully from:\n{filename}")
                    
                except json.JSONDecodeError:
                    messagebox.showerror("Error", "Invalid JSON file format")
                except PermissionError:
                    messagebox.showerror("Error", "Cannot read file. Check permissions.")
                except Exception as e:
                    print(f"File read error: {str(e)}")
                    messagebox.showerror("Error", f"Failed to read file: {str(e)}")
                
            except Exception as e:
                print(f"File dialog error: {str(e)}")
                messagebox.showerror("Error", "Failed to open file dialog")
                
        except Exception as e:
            print(f"Load error details: {str(e)}")
            messagebox.showerror("Error", "Unexpected error during load operation")

    def load_mix_data(self, data):
        """Load mix design data into input fields"""
        try:
            # Map of data keys to widget names
            widget_map = {
                "Grade Designation": self.grade_entry,
                "Mineral Admixture": self.mineral_admixture_var,
                "Nominal Size": self.nominal_size_entry,
                "Workability": self.workability_entry,
                "Exposure Condition": self.exposure_conditions_var,
                "Pump Concrete": self.pump_concrete_var,
                "Aggregate Type": self.type_of_aggregate_var,
                "Chemical Admixture": self.chemical_admixture_var,
                "Cement SG": self.cement_sg_entry,
                "Coarse Aggregate SG": self.coarse_agg_sg_entry,
                "Fine Aggregate SG": self.fine_agg_sg_entry,
                "Chemical Admixture SG": self.chem_admixture_sg_entry,
                "Coarse Aggregate Water Absorption": self.coarse_agg_water_absorption_entry,
                "Fine Aggregate Water Absorption": self.fine_agg_water_absorption_entry,
                "Fine Aggregate Zone": self.zone_of_fine_aggregate_var,
                "Coarse Aggregate Surface Moisture": self.coarse_agg_surface_moisture_entry,
                "Fine Aggregate Surface Moisture": self.fine_agg_surface_moisture_entry,
                "Fly Ash SG": self.flyash_sg_entry
            }
            
            # Load each value into its corresponding widget
            for key, widget in widget_map.items():
                if key in data:
                    value = data[key]
                    if isinstance(widget, ttk.Entry):
                        widget.delete(0, tk.END)
                        widget.insert(0, str(value))
                    elif isinstance(widget, tk.StringVar):
                        widget.set(str(value))
                    
        except Exception as e:
            print(f"Data loading error: {str(e)}")
            raise ValueError(f"Failed to load mix design data: {str(e)}")

    def change_unit_system(self, system):
        """Change between metric and imperial units"""
        if system != self.unit_system.get():
            self.unit_system.set(system)
            self.convert_units()
            messagebox.showinfo("Units Changed", f"Units changed to {system} system")

    def convert_units(self):
        """Convert values between metric and imperial units"""
        conversion_factors = {
            "Metric to Imperial": {
                "length": 3.28084,  # meters to feet
                "volume": 35.3147,  # cubic meters to cubic feet
                "mass": 2.20462,    # kg to lb
                "pressure": 145.038  # MPa to psi
            },
            "Imperial to Metric": {
                "length": 0.3048,   # feet to meters
                "volume": 0.0283168, # cubic feet to cubic meters
                "mass": 0.453592,    # lb to kg
                "pressure": 0.00689476 # psi to MPa
            }
        }
        
        try:
            if self.unit_system.get() == "Imperial":
                factors = conversion_factors["Metric to Imperial"]
                # Convert input fields
                self.convert_entry_value(self.nominal_size_entry, factors["length"])
                self.convert_entry_value(self.workability_entry, factors["length"])
                
                # Convert results if they exist
                if hasattr(self, 'current_results'):
                    self.convert_results_to_imperial()
            else:
                factors = conversion_factors["Imperial to Metric"]
                # Convert input fields
                self.convert_entry_value(self.nominal_size_entry, factors["length"])
                self.convert_entry_value(self.workability_entry, factors["length"])
                
                # Convert results if they exist
                if hasattr(self, 'current_results'):
                    self.convert_results_to_metric()
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert units: {str(e)}")

    def convert_entry_value(self, entry_widget, factor):
        """Convert a single entry widget value"""
        try:
            current_value = float(entry_widget.get())
            new_value = current_value * factor
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, f"{new_value:.2f}")
        except ValueError:
            pass

    def convert_results_to_imperial(self):
        """Convert results from metric to imperial units"""
        if hasattr(self, 'current_results'):
            # Implementation of result conversion to imperial units
            pass

    def convert_results_to_metric(self):
        """Convert results from imperial to metric units"""
        if hasattr(self, 'current_results'):
            # Implementation of result conversion to metric units
            pass

    def show_cost_calculator(self):
        """Show cost calculator window"""
        if not hasattr(self, 'current_results'):
            messagebox.showerror("Error", "Please calculate a mix design first!")
            return
            
        cost_window = tk.Toplevel(self.root)
        cost_window.title("Cost Calculator")
        cost_window.geometry("600x800")
        
        # Create frames
        input_frame = ttk.LabelFrame(cost_window, text="Material Costs", padding=10)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        result_frame = ttk.LabelFrame(cost_window, text="Cost Analysis", padding=10)
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Cost input fields
        cost_entries = {}
        
        row = 0
        for material in ['Cement (per 50kg bag)', 'Water (per m³)', 
                        'Fine Aggregate (per m³)', 'Coarse Aggregate (per m³)',
                        'Chemical Admixture (per kg)', 'Fly Ash (per kg)']:
            ttk.Label(input_frame, text=material + ":").grid(row=row, column=0, sticky='w', pady=5)
            entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
            entry.grid(row=row, column=1, sticky='w', pady=5)
            entry.insert(0, "0.0")
            cost_entries[material] = entry
            row += 1
        
        # Results display
        result_text = tk.Text(result_frame, height=25, width=70)
        result_text.pack(pady=5, padx=5)
        
        def calculate_cost():
            try:
                # Get unit costs
                cement_cost = float(cost_entries['Cement (per 50kg bag)'].get())
                water_cost = float(cost_entries['Water (per m³)'].get())
                fa_cost = float(cost_entries['Fine Aggregate (per m³)'].get())
                ca_cost = float(cost_entries['Coarse Aggregate (per m³)'].get())
                admix_cost = float(cost_entries['Chemical Admixture (per kg)'].get())
                flyash_cost = float(cost_entries['Fly Ash (per kg)'].get())
                
                # Get quantities from trail mix result
                trail_mix = self.current_results['trail_mix_result']
                lines = trail_mix.split('\n')
                quantities = {}
                
                # Parse the trail mix result
                for line in lines:
                    line = line.strip()
                    if ': ' in line:
                        # Remove any numbering at the start (e.g., "1. ")
                        if line[0].isdigit() and '. ' in line:
                            line = line.split('. ', 1)[1]
                        
                        key, value = line.split(': ')
                        key = key.strip()
                        # Extract numeric value and handle units
                        if 'kg' in value or 'Lit' in value:
                            value = float(value.split()[0])
                            quantities[key] = value

                # Print debug info
                print("Parsed Quantities:", quantities)
                print(f"Trail Mix Result:\n{trail_mix}")
                
                # Calculate costs
                cement_total = quantities.get('Cement', 0) * (cement_cost / 50)  # Convert to cost per kg
                water_total = quantities.get('Water', 0) * (water_cost / 1000)  # Convert to cost per liter
                fa_total = quantities.get('Fine Aggregate', 0) * (fa_cost / 1000)  # Convert to cost per kg
                ca_total = quantities.get('Coarse Aggregate', 0) * (ca_cost / 1000)  # Convert to cost per kg
                admix_total = quantities.get('Chemical Admixture', 0) * admix_cost
                flyash_total = quantities.get('Fly Ash', 0) * flyash_cost if 'Fly Ash' in quantities else 0
                
                total_cost = cement_total + water_total + fa_total + ca_total + admix_total + flyash_total
                
                # Calculate percentages safely
                def safe_percentage(value, total):
                    return (value / total * 100) if total > 0 else 0
                
                # Display results
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"""COST ANALYSIS PER CUBIC METER
{'='*50}

MATERIAL COSTS:
{'-'*50}
• Cement:             {cement_total:.2f} (@ {cement_cost:.2f} per bag)
• Water:              {water_total:.2f} (@ {water_cost:.2f} per m³)
• Fine Aggregate:     {fa_total:.2f} (@ {fa_cost:.2f} per m³)
• Coarse Aggregate:   {ca_total:.2f} (@ {ca_cost:.2f} per m³)
• Chemical Admixture: {admix_total:.2f} (@ {admix_cost:.2f} per kg)
• Fly Ash:            {flyash_total:.2f} (@ {flyash_cost:.2f} per kg)
{'-'*50}
TOTAL COST PER m³:    {total_cost:.2f}

COST BREAKDOWN:
{'-'*50}
• Cement:             {safe_percentage(cement_total, total_cost):.1f}%
• Water:              {safe_percentage(water_total, total_cost):.1f}%
• Fine Aggregate:     {safe_percentage(fa_total, total_cost):.1f}%
• Coarse Aggregate:   {safe_percentage(ca_total, total_cost):.1f}%
• Chemical Admixture: {safe_percentage(admix_total, total_cost):.1f}%
• Fly Ash:            {safe_percentage(flyash_total, total_cost):.1f}%

MATERIAL QUANTITIES:
{'-'*50}
• Cement:             {quantities.get('Cement', 0):.1f} kg ({quantities.get('Cement', 0)/50:.1f} bags)
• Water:              {quantities.get('Water', 0):.1f} L
• Fine Aggregate:     {quantities.get('Fine Aggregate', 0):.1f} kg
• Coarse Aggregate:   {quantities.get('Coarse Aggregate', 0):.1f} kg
• Chemical Admixture: {quantities.get('Chemical Admixture', 0):.1f} kg
• Fly Ash:            {quantities.get('Fly Ash', 0):.1f} kg

NOTES:
{'-'*50}
1. All costs are calculated per cubic meter of concrete
2. Transportation costs are not included
3. Labor costs are not included
4. Equipment costs are not included
5. Overhead costs are not included
""")
            
            except ValueError as ve:
                messagebox.showerror("Input Error", "Please enter valid numbers for all costs")
            except Exception as e:
                messagebox.showerror("Calculation Error", f"Failed to calculate costs: {str(e)}")
        
        # Calculate button
        ttk.Button(input_frame, text="Calculate Costs", command=calculate_cost).grid(row=row, column=0, columnspan=2, pady=10)
        
        # Help button
        def show_help():
            help_text = """Cost Calculator Help:

1. Input Guidelines:
   - Enter all costs in your local currency
   - Cement cost is per 50kg bag
   - Aggregate costs are per cubic meter
   - Water cost is per cubic meter
   - Admixture cost is per kg

2. Notes:
   - Costs are calculated based on the current mix design
   - All quantities are automatically loaded from mix design
   - Percentages show the cost distribution
   - Additional costs (transport, labor) are not included

3. Tips:
   - Update costs regularly for accurate estimates
   - Consider bulk pricing for large projects
   - Verify all costs with suppliers
   - Keep records of cost variations"""
            
            messagebox.showinfo("Cost Calculator Help", help_text)
        
        ttk.Button(input_frame, text="Help", command=show_help).grid(row=row+1, column=0, columnspan=2, pady=5)

    def show_mix_history(self):
        """Show mix design history window"""
        history_window = tk.Toplevel(self.root)
        history_window.title("Mix Design History")
        history_window.geometry("800x600")
        
        # Create treeview for history
        columns = ("Date", "Grade", "Strength", "W/C Ratio", "Cement", "Fly Ash", "Water", "Fine Agg", "Coarse Agg")
        tree = ttk.Treeview(history_window, columns=columns, show='headings')
        
        # Set column headings and widths
        column_widths = {
            "Date": 150,
            "Grade": 80,
            "Strength": 100,
            "W/C Ratio": 100,
            "Cement": 100,
            "Fly Ash": 100,
            "Water": 100,
            "Fine Agg": 100,
            "Coarse Agg": 100
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=column_widths[col])
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(history_window, orient="vertical", command=tree.yview)
        x_scrollbar = ttk.Scrollbar(history_window, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Pack widgets
        tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        history_window.grid_rowconfigure(0, weight=1)
        history_window.grid_columnconfigure(0, weight=1)
        
        # Add history entries
        for mix in reversed(self.mix_design_history):  # Show newest first
            tree.insert("", "end", values=(
                mix["date"],
                mix["grade"],
                f"{mix['strength']:.1f} MPa",
                f"{mix['wc_ratio']:.3f}",
                f"{mix['cement']:.1f} kg",
                f"{mix.get('fly_ash', '-')}" if isinstance(mix.get('fly_ash'), (int, float)) else "-",
                f"{mix['water']:.1f} L",
                f"{mix['fine_agg']:.1f} kg",
                f"{mix['coarse_agg']:.1f} kg"
            ))
        
        # Add control buttons
        button_frame = ttk.Frame(history_window)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def export_history():
            try:
                filename = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    initialfile="mix_design_history.xlsx"
                )
                
                if filename:
                    # Convert history to DataFrame
                    df = pd.DataFrame(self.mix_design_history)
                    
                    # Reorder and rename columns
                    columns = {
                        'date': 'Date',
                        'grade': 'Grade',
                        'strength': 'Strength (MPa)',
                        'wc_ratio': 'W/C Ratio',
                        'cement': 'Cement (kg)',
                        'fly_ash': 'Fly Ash (kg)',
                        'water': 'Water (L)',
                        'fine_agg': 'Fine Aggregate (kg)',
                        'coarse_agg': 'Coarse Aggregate (kg)',
                        'admixture': 'Chemical Admixture (kg)',
                        'cement_saved': 'Cement Saved (kg)'
                    }
                    
                    df = df.rename(columns=columns)
                    df = df[[col for col in columns.values() if col in df.columns]]
                    
                    # Export to Excel
                    df.to_excel(filename, index=False, sheet_name='Mix Design History')
                    messagebox.showinfo("Success", "History exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export history: {str(e)}")
        
        def clear_history():
            if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all mix design history?"):
                self.mix_design_history = []
                tree.delete(*tree.get_children())
                try:
                    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mix_history.json')
                    if os.path.exists(history_file):
                        os.remove(history_file)
                except Exception as e:
                    print(f"Failed to delete history file: {str(e)}")
        
        ttk.Button(button_frame, text="Export History", command=export_history).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear History", command=clear_history).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Close", command=history_window.destroy).pack(side="left", padx=5)

    def show_mix_comparison(self):
        """Show mix design comparison window"""
        if not self.mix_design_history:
            messagebox.showerror("Error", "No mix designs available for comparison. Please calculate some mix designs first.")
            return
        
        comparison_window = tk.Toplevel(self.root)
        comparison_window.title("Mix Design Comparison")
        comparison_window.geometry("800x600")
        
        # Create frames
        control_frame = ttk.Frame(comparison_window)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Add mix selection
        ttk.Label(control_frame, text="Select Mix Designs to Compare:").pack(side='left')
        mix1_var = tk.StringVar()
        mix2_var = tk.StringVar()
        
        # Get available mix IDs
        mix_ids = [str(mix["id"]) for mix in self.mix_design_history]
        
        # Create comboboxes for mix selection
        mix1_combo = ttk.Combobox(control_frame, textvariable=mix1_var, values=mix_ids, width=20)
        mix1_combo.pack(side='left', padx=5)
        mix2_combo = ttk.Combobox(control_frame, textvariable=mix2_var, values=mix_ids, width=20)
        mix2_combo.pack(side='left', padx=5)
        
        # Compare button
        ttk.Button(control_frame, text="Compare", 
                  command=lambda: self.compare_mixes(mix1_var.get(), mix2_var.get())).pack(side='left', padx=5)
        
        # Results display
        self.comparison_text = tk.Text(comparison_window, height=30, width=80)
        self.comparison_text.pack(pady=10, padx=10)

    def compare_mixes(self, mix1_id, mix2_id):
        """Compare two mix designs and display the differences"""
        try:
            if not mix1_id or not mix2_id:
                messagebox.showerror("Error", "Please select two mix designs to compare")
                return
            
            # Get mix designs from history
            mix1 = next((mix for mix in self.mix_design_history if str(mix["id"]) == mix1_id), None)
            mix2 = next((mix for mix in self.mix_design_history if str(mix["id"]) == mix2_id), None)
            
            if not mix1 or not mix2:
                messagebox.showerror("Error", "Could not find selected mix designs")
                return
            
            # Compare and display results
            comparison_text = f"""Mix Design Comparison
            
            Parameter          Mix 1           Mix 2           Difference
            ---------------------------------------------------------
            Grade:            {mix1['grade']}          {mix2['grade']}          -
            Strength:         {mix1['strength']:.1f} MPa      {mix2['strength']:.1f} MPa      {mix2['strength'] - mix1['strength']:.1f} MPa
            W/C Ratio:        {mix1['wc_ratio']:.3f}         {mix2['wc_ratio']:.3f}         {mix2['wc_ratio'] - mix1['wc_ratio']:.3f}
            Cement:           {mix1['cement']:.1f} kg      {mix2['cement']:.1f} kg      {mix2['cement'] - mix1['cement']:.1f} kg
            Water:            {mix1['water']:.1f} L       {mix2['water']:.1f} L       {mix2['water'] - mix1['water']:.1f} L
            Fine Agg:         {mix1['fine_agg']:.1f} kg      {mix2['fine_agg']:.1f} kg      {mix2['fine_agg'] - mix1['fine_agg']:.1f} kg
            Coarse Agg:       {mix1['coarse_agg']:.1f} kg      {mix2['coarse_agg']:.1f} kg      {mix2['coarse_agg'] - mix1['coarse_agg']:.1f} kg
            """
            
            self.comparison_text.delete(1.0, tk.END)
            self.comparison_text.insert(tk.END, comparison_text)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compare mix designs: {str(e)}")
            print(f"Comparison error details: {str(e)}")  # For debugging

    def show_temperature_calculator(self):
        """Show temperature effects calculator window"""
        temp_window = tk.Toplevel(self.root)
        temp_window.title("Temperature Effects Calculator")
        temp_window.geometry("400x500")
        
        # Create input fields
        input_frame = ttk.Frame(temp_window)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        # Temperature inputs
        ttk.Label(input_frame, text="Concrete Temperature (°C):").grid(row=0, column=0, sticky='w', pady=5)
        temp_entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
        temp_entry.grid(row=0, column=1, sticky='w', pady=5)
        temp_entry.insert(0, "20.0")
        
        ttk.Label(input_frame, text="Ambient Temperature (°C):").grid(row=1, column=0, sticky='w', pady=5)
        ambient_entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
        ambient_entry.grid(row=1, column=1, sticky='w', pady=5)
        ambient_entry.insert(0, "25.0")
        
        ttk.Label(input_frame, text="Relative Humidity (%):").grid(row=2, column=0, sticky='w', pady=5)
        humidity_entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
        humidity_entry.grid(row=2, column=1, sticky='w', pady=5)
        humidity_entry.insert(0, "65.0")
        
        # Calculate button
        ttk.Button(temp_window, text="Calculate Effects", 
                  command=lambda: self.calculate_temperature_effects(
                      float(temp_entry.get()),
                      float(ambient_entry.get()),
                      float(humidity_entry.get())
                  )).pack(pady=10)
        
        # Results display
        self.temp_result_text = tk.Text(temp_window, height=15, width=40)
        self.temp_result_text.pack(pady=10, padx=10)

    def calculate_temperature_effects(self, concrete_temp, ambient_temp, humidity):
        """Calculate temperature effects on concrete properties"""
        try:
            # Calculate temperature effects
            temp_diff = concrete_temp - ambient_temp
            
            # Estimate setting time adjustment
            if temp_diff > 0:
                setting_time_factor = 1.0 - (temp_diff * 0.05)  # 5% reduction per degree above ambient
            else:
                setting_time_factor = 1.0 + (abs(temp_diff) * 0.05)  # 5% increase per degree below ambient
            
            # Estimate strength development
            strength_factor = 1.0
            if concrete_temp > 32:
                strength_factor -= (concrete_temp - 32) * 0.02  # 2% reduction per degree above 32°C
            elif concrete_temp < 10:
                strength_factor -= (10 - concrete_temp) * 0.02  # 2% reduction per degree below 10°C
            
            # Estimate evaporation rate
            evap_rate = 0.1 * (1 + (concrete_temp - ambient_temp) * 0.05) * (1 - humidity/100)
            
            # Display results
            result_text = f"""Temperature Effects Analysis:
            
            1. Setting Time:
               - Adjustment Factor: {setting_time_factor:.2f}
               - {' Faster' if setting_time_factor < 1 else ' Slower'} setting time
            
            2. Strength Development:
               - Strength Factor: {strength_factor:.2f}
               - Expected strength: {strength_factor * 100:.1f}% of design strength
            
            3. Evaporation Rate:
               - Rate: {evap_rate:.3f} kg/m²/h
               - Risk Level: {'High' if evap_rate > 1.0 else 'Moderate' if evap_rate > 0.5 else 'Low'}
            
            Recommendations:
            {self.get_temperature_recommendations(concrete_temp, ambient_temp, humidity, evap_rate)}
            """
            
            self.temp_result_text.delete(1.0, tk.END)
            self.temp_result_text.insert(tk.END, result_text)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate temperature effects: {str(e)}")

    def get_temperature_recommendations(self, concrete_temp, ambient_temp, humidity, evap_rate):
        """Get recommendations based on temperature conditions"""
        recommendations = []
        
        if concrete_temp > 32:
            recommendations.append("- Use ice or chilled water to reduce concrete temperature")
            recommendations.append("- Consider night placement")
            recommendations.append("- Protect from direct sunlight")
        
        if concrete_temp < 10:
            recommendations.append("- Use hot water in the mix")
            recommendations.append("- Protect concrete from cold weather")
            recommendations.append("- Consider using accelerating admixtures")
        
        if evap_rate > 1.0:
            recommendations.append("- Apply evaporation retarder")
            recommendations.append("- Use wind breaks")
            recommendations.append("- Fog spray during finishing")
        
        if humidity < 40:
            recommendations.append("- Increase curing duration")
            recommendations.append("- Use curing compounds")
        
        return "\n".join(recommendations) if recommendations else "No special measures required"

    def show_batch_calculator(self):
        """Show batch size calculator window"""
        if not hasattr(self, 'current_results'):
            messagebox.showerror("Error", "Please calculate a mix design first!")
            return
            
        batch_window = tk.Toplevel(self.root)
        batch_window.title("Batch Size Calculator")
        batch_window.geometry("600x800")
        
        # Create frames
        input_frame = ttk.LabelFrame(batch_window, text="Batch Parameters", padding=10)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        result_frame = ttk.LabelFrame(batch_window, text="Batch Quantities", padding=10)
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Batch size input
        ttk.Label(input_frame, text="Required Batch Size (m³):").grid(row=0, column=0, sticky='w', pady=5)
        batch_size_entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
        batch_size_entry.grid(row=0, column=1, sticky='w', pady=5)
        batch_size_entry.insert(0, "1.0")
        
        # Safety factor input
        ttk.Label(input_frame, text="Safety Factor (%):").grid(row=1, column=0, sticky='w', pady=5)
        safety_factor_entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
        safety_factor_entry.grid(row=1, column=1, sticky='w', pady=5)
        safety_factor_entry.insert(0, "10.0")
        
        # Number of batches input
        ttk.Label(input_frame, text="Number of Batches:").grid(row=2, column=0, sticky='w', pady=5)
        batches_entry = ttk.Entry(input_frame, validate="key", validatecommand=self.validators['float'])
        batches_entry.grid(row=2, column=1, sticky='w', pady=5)
        batches_entry.insert(0, "1")
        
        # Results display
        result_text = tk.Text(result_frame, height=25, width=70)
        result_text.pack(pady=5, padx=5)
        
        def calculate_batch():
            try:
                batch_size = float(batch_size_entry.get())
                safety_factor = float(safety_factor_entry.get())
                num_batches = int(batches_entry.get())
                
                if batch_size <= 0 or safety_factor < 0 or num_batches <= 0:
                    raise ValueError("All values must be positive!")
                
                # Get current mix quantities from trail mix result
                trail_mix = self.current_results['trail_mix_result']
                lines = trail_mix.split('\n')
                quantities = {}
                
                # Parse the trail mix result
                for line in lines:
                    line = line.strip()
                    if ': ' in line:
                        # Remove any numbering at the start (e.g., "1. ")
                        if line[0].isdigit() and '. ' in line:
                            line = line.split('. ', 1)[1]
                        
                        key, value = line.split(': ')
                        key = key.strip()
                        # Extract numeric value and handle units
                        if 'kg' in value or 'Lit' in value:
                            value = float(value.split()[0])
                            quantities[key] = value
                
                # Calculate per batch quantities
                cement_per_batch = quantities.get('Cement', 0) * batch_size * (1 + safety_factor/100)
                water_per_batch = quantities.get('Water', 0) * batch_size * (1 + safety_factor/100)
                fa_per_batch = quantities.get('Fine Aggregate', 0) * batch_size * (1 + safety_factor/100)
                ca_per_batch = quantities.get('Coarse Aggregate', 0) * batch_size * (1 + safety_factor/100)
                admix_per_batch = quantities.get('Chemical Admixture', 0) * batch_size * (1 + safety_factor/100)
                
                # Calculate total quantities
                total_cement = cement_per_batch * num_batches
                total_water = water_per_batch * num_batches
                total_fa = fa_per_batch * num_batches
                total_ca = ca_per_batch * num_batches
                total_admix = admix_per_batch * num_batches
                
                # Display results
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"""BATCH CALCULATIONS
{'='*50}

PER BATCH QUANTITIES (including {safety_factor}% safety factor):
{'-'*50}
• Cement:             {cement_per_batch:.1f} kg ({cement_per_batch/50:.1f} bags)
• Water:              {water_per_batch:.1f} L
• Fine Aggregate:     {fa_per_batch:.1f} kg
• Coarse Aggregate:   {ca_per_batch:.1f} kg
• Chemical Admixture: {admix_per_batch:.1f} kg

TOTAL QUANTITIES FOR {num_batches} BATCH(ES):
{'-'*50}
• Cement:             {total_cement:.1f} kg ({total_cement/50:.1f} bags)
• Water:              {total_water:.1f} L
• Fine Aggregate:     {total_fa:.1f} kg
• Coarse Aggregate:   {total_ca:.1f} kg
• Chemical Admixture: {total_admix:.1f} kg

NOTES:
{'-'*50}
1. All quantities include {safety_factor}% safety factor
2. Cement is calculated in 50kg bags
3. Adjust water based on aggregate moisture content
4. Check admixture dosage with manufacturer specs
5. Verify quantities before batching
""")

                # Print debug info
                print("Parsed Quantities:", quantities)
                print(f"Trail Mix Result:\n{trail_mix}")
            
            except ValueError as ve:
                messagebox.showerror("Input Error", str(ve))
            except Exception as e:
                messagebox.showerror("Calculation Error", f"Failed to calculate batch quantities: {str(e)}")
        
        # Calculate button
        ttk.Button(input_frame, text="Calculate Batch Quantities", command=calculate_batch).grid(row=3, column=0, columnspan=2, pady=10)

    def get_save_directory(self):
        """Get the save directory path and ensure it exists"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.join(base_dir, 'saved_designs')
        export_dir = os.path.join(base_dir, 'exports')
        
        # Create directories if they don't exist
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(export_dir, exist_ok=True)
        
        return save_dir, export_dir

    def show_save_locations(self):
        """Show the user where files are being saved"""
        try:
            # Get the base directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Create directories if they don't exist
            saved_designs_dir = os.path.join(base_dir, 'saved_designs')
            exports_dir = os.path.join(base_dir, 'exports')
            
            os.makedirs(saved_designs_dir, exist_ok=True)
            os.makedirs(exports_dir, exist_ok=True)
            
            # Prepare the message
            message = f"""File Save Locations:

1. Mix Design Files (JSON):
   {saved_designs_dir}

2. Exports (PDF & Excel):
   {exports_dir}

Note: These folders will be created automatically if they don't exist.
You can also choose a different location when saving."""

            # Show the message in an info dialog
            messagebox.showinfo("Save Locations", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not access save locations: {str(e)}")

    def export_to_excel(self):
        """Export current mix design results to Excel"""
        if not hasattr(self, 'current_results'):
            messagebox.showerror("Error", "No results to export. Please calculate first.")
            return
            
        try:
            # Get export directory and ensure it exists
            base_dir = os.path.dirname(os.path.abspath(__file__))
            export_dir = os.path.join(base_dir, 'exports')
            os.makedirs(export_dir, exist_ok=True)

            try:
                default_name = f"mix_design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                filename = filedialog.asksaveasfilename(
                    initialdir=export_dir,
                    initialfile=default_name,
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    parent=self.root
                )
                
                if filename:
                    try:
                        # Ensure the file will be saved in exports directory
                        final_path = os.path.join(export_dir, os.path.basename(filename))
                        
                        # Check if file exists
                        if os.path.exists(final_path):
                            if not messagebox.askyesno("Confirm Overwrite", 
                                f"File {os.path.basename(final_path)} already exists.\nDo you want to overwrite it?"):
                                return

                        # Get input parameters and results
                        input_data = self.get_current_mix_data()
                        
                        # Replace special characters for Excel compatibility
                        clean_input_data = {}
                        for k, v in input_data.items():
                            k = str(k).replace('³', '3').replace('²', '2')
                            v = str(v).replace('³', '3').replace('²', '2')
                            clean_input_data[k] = v
                        
                        # Create Excel writer
                        with pd.ExcelWriter(final_path, engine='openpyxl') as writer:
                            # Write input parameters
                            df_inputs = pd.DataFrame(list(clean_input_data.items()), 
                                                  columns=['Parameter', 'Value'])
                            df_inputs.to_excel(writer, sheet_name='Input Parameters', 
                                             index=False, encoding='utf-8')
                            
                            # Process results data
                            results_data = []
                            for section, content in self.current_results.items():
                                section_name = section.replace('_result', '').replace('_', ' ').title()
                                results_data.append([section_name, ''])
                                
                                for line in content.strip().split('\n'):
                                    if not line.strip():
                                        continue
                                    # Clean special characters
                                    line = line.replace('³', '3').replace('²', '2')
                                    if line.startswith('\t'):
                                        results_data.append(['', line.strip()])
                                    else:
                                        clean_line = line.strip()
                                        if clean_line[0].isdigit() and '. ' in clean_line:
                                            clean_line = clean_line.split('. ', 1)[1]
                                        results_data.append(['', clean_line])
                                
                                results_data.append(['', ''])
                            
                            # Create results sheet
                            df_results = pd.DataFrame(results_data, columns=['Section', 'Details'])
                            df_results.to_excel(writer, sheet_name='Results', 
                                              index=False, encoding='utf-8')
                            
                            # Auto-adjust column widths
                            for sheet in writer.sheets.values():
                                for idx, col in enumerate(sheet.columns):
                                    max_length = max(len(str(cell.value or "")) 
                                                   for cell in col)
                                    sheet.column_dimensions[chr(65 + idx)].width = min(
                                        max_length + 2, 100)
                        
                        messagebox.showinfo("Success", 
                            f"Results exported to Excel successfully!\nLocation: {final_path}")
                        
                    except PermissionError:
                        messagebox.showerror("Permission Error", 
                            "Cannot write to file. Please check your permissions.")
                    except Exception as e:
                        print(f"Excel generation error: {str(e)}")
                        messagebox.showerror("Export Error", 
                            "Failed to generate Excel file. Please try again.")
                        
            except Exception as e:
                print(f"File dialog error: {str(e)}")
                messagebox.showerror("Error", "Failed to open save dialog")
                
        except Exception as e:
            print(f"Excel export error: {str(e)}")
            messagebox.showerror("Error", "Unexpected error during Excel export.")

def main():
    root = tk.Tk()
    app = MixDesignCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
