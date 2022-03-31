// pygenda_clipboard.c
//
// Small C library to interface Pygenda with GTK clipboard.
// Allows Pygenda entries to be copied to the clipboard.
// Note: Pasting is done in the Python code (pygenda_gui.py).
//
// Copyright (C) 2022 Matthew Lewis
//
// This file is part of Pygenda.
//
// Pygenda is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, version 3.
//
// Pygenda is distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
// General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pygenda. If not, see <https://www.gnu.org/licenses/>.
//

#include <stdlib.h>
#include <string.h>
#include <gtk/gtk.h>

// Constants

// Enumerated types of clipboard selection data we can store:
#define DATA_TXT_PLAIN (0)
#define DATA_TXT_CALENDAR (1)
// Number of data types
#define LEN_SELECTION_DATA (2)

// Map requested types (strings) to our enumerated types
GtkTargetEntry target_array[] = {
	{"text/plain;charset=utf-8", 0, DATA_TXT_PLAIN},
	{"UTF8_STRING", 0, DATA_TXT_PLAIN},
	{"TEXT", 0, DATA_TXT_PLAIN},
	{"STRING", 0, DATA_TXT_PLAIN},
	{"text/calendar", 0, DATA_TXT_CALENDAR}
};

// Macro for length of target_array[]
#define LEN_TARGET_ARRAY (sizeof(target_array)/sizeof(GtkTargetEntry))

// We store pointers to our data here:
// Assume this is zero initialised
char *selectionStr[LEN_SELECTION_DATA];

// Callback - called when data is requested
// type_idx is set to enumerated value type
void cb_get_fn(GtkClipboard* clipboard, GtkSelectionData* selection_data, guint type_idx, gpointer ptr) {
	switch(type_idx) {
	case DATA_TXT_PLAIN:
		gtk_selection_data_set_text(selection_data, selectionStr[DATA_TXT_PLAIN], -1);
		break;
	case DATA_TXT_CALENDAR:
		gtk_selection_data_set(selection_data, gdk_atom_intern("text/calendar", FALSE),8,selectionStr[type_idx], strlen(selectionStr[type_idx]));
		break;
	}
}

// Callback - called when data is no longer needed (e.g. something
// else is copied)
void cb_clear_fn(GtkClipboard* clipboard, gpointer ptr) {
	int i=0;
	for ( ; i<LEN_SELECTION_DATA ; i++) {
		free(selectionStr[i]);
		selectionStr[i] = NULL;
	}
}

// exported function used by pygenda
void set_cb(char *txt, char* txtcal) {
	// Set callbacks for clipboard
	GtkClipboard *cb = gtk_clipboard_get(GDK_SELECTION_CLIPBOARD);
	gtk_clipboard_set_with_data(cb, target_array, LEN_TARGET_ARRAY, cb_get_fn, cb_clear_fn, NULL);
	// cb_clear_fn() should have been called so pointers should be null here

	// Take copies of strings that we own here
	selectionStr[DATA_TXT_PLAIN] = malloc(strlen(txt)+1);
	strcpy(selectionStr[DATA_TXT_PLAIN],txt);
	selectionStr[DATA_TXT_CALENDAR] = malloc(strlen(txtcal)+1);
	strcpy(selectionStr[DATA_TXT_CALENDAR],txtcal);

	//gtk_clipboard_store(cb); // This doesn't seem to work??
}
