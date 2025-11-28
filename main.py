import sys
import sqlite3

from PySide6.QtWidgets import (
    QApplication,
    QTableWidgetItem,
    QTableWidget,
    QPushButton,
    QMessageBox,
    QInputDialog,
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

DB_PATH = r"C:\Users\gauta\Fantasy_cricket\fantasy_cricket.db"
MAX_PLAYERS = 11
MAX_CREDITS = 100


def ensure_team_tables(cur):
    """Create teams and team_players tables if they don't exist."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            total_credits INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS team_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            FOREIGN KEY(team_id) REFERENCES teams(id),
            FOREIGN KEY(player_id) REFERENCES players(id)
        );
        """
    )


class FantasyApp:
    def __init__(self):
        # Qt loader and UI
        loader = QUiLoader()
        ui_file = QFile("fantasy_cricket.ui")
        if not ui_file.open(QFile.ReadOnly):
            print("ERROR: Cannot open fantasy_cricket.ui")
            sys.exit(1)

        self.window = loader.load(ui_file)
        ui_file.close()

        if self.window is None:
            print("ERROR: Failed to load UI")
            sys.exit(1)

        self.window.setWindowTitle("Fantasy Cricket Game")

        # Widgets
        self.player_table: QTableWidget = self.window.findChild(QTableWidget, "playerTable")
        self.team_table: QTableWidget = self.window.findChild(QTableWidget, "teamTable")
        self.save_button: QPushButton = self.window.findChild(QPushButton, "saveButton")

        if self.player_table is None or self.team_table is None or self.save_button is None:
            print("ERROR: Could not find widgets in UI")
            sys.exit(1)

        # DB connection
        self.conn = sqlite3.connect(DB_PATH)
        self.cur = self.conn.cursor()
        ensure_team_tables(self.cur)

        # Debug: how many players?
        self.cur.execute("SELECT COUNT(*) FROM players")
        print("DEBUG: players in DB =", self.cur.fetchone()[0])

        # Configure tables
        for table in (self.player_table, self.team_table):
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)

        # Connect events
        self.player_table.itemDoubleClicked.connect(self.add_player_to_team)
        self.team_table.itemDoubleClicked.connect(self.remove_player_from_team)
        self.save_button.clicked.connect(self.save_team)

        # Initial data
        self.load_players()
        self.setup_team_table()

    # ---------- Load data into Available Players ----------

    def load_players(self):
        self.cur.execute(
            "SELECT id, name, team, role, credits FROM players ORDER BY role, name"
        )
        rows = self.cur.fetchall()

        self.player_table.setRowCount(len(rows))
        self.player_table.setColumnCount(5)
        self.player_table.setHorizontalHeaderLabels(
            ["ID", "Name", "Team", "Role", "Credits"]
        )

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.player_table.setItem(r, c, QTableWidgetItem(str(value)))

        # Hide ID from user
        self.player_table.setColumnHidden(0, True)
        self.player_table.resizeColumnsToContents()

    # ---------- Setup right table ----------

    def setup_team_table(self):
        self.team_table.setRowCount(0)
        self.team_table.setColumnCount(5)
        self.team_table.setHorizontalHeaderLabels(
            ["ID", "Name", "Team", "Role", "Credits"]
        )
        self.team_table.setColumnHidden(0, True)
        self.team_table.resizeColumnsToContents()

    # ---------- Helper functions ----------

    def team_credits(self) -> int:
        total = 0
        for r in range(self.team_table.rowCount()):
            total += int(self.team_table.item(r, 4).text())
        return total

    def team_has_player(self, pid: int) -> bool:
        for r in range(self.team_table.rowCount()):
            if int(self.team_table.item(r, 0).text()) == pid:
                return True
        return False

    # ---------- Events ----------

    def add_player_to_team(self, item):
        row = item.row()
        pid = int(self.player_table.item(row, 0).text())
        name = self.player_table.item(row, 1).text()
        team = self.player_table.item(row, 2).text()
        role = self.player_table.item(row, 3).text()
        credits = int(self.player_table.item(row, 4).text())

        if self.team_has_player(pid):
            QMessageBox.information(self.window, "Already added", "Player already in team.")
            return

        if self.team_table.rowCount() >= MAX_PLAYERS:
            QMessageBox.warning(
                self.window, "Limit reached", f"Maximum {MAX_PLAYERS} players allowed."
            )
            return

        if self.team_credits() + credits > MAX_CREDITS:
            QMessageBox.warning(
                self.window,
                "Credit limit exceeded",
                f"Total credits cannot exceed {MAX_CREDITS}.",
            )
            return

        new_row = self.team_table.rowCount()
        self.team_table.insertRow(new_row)
        for c, v in enumerate([pid, name, team, role, credits]):
            self.team_table.setItem(new_row, c, QTableWidgetItem(str(v)))

        self.team_table.resizeColumnsToContents()

    def remove_player_from_team(self, item):
        row = item.row()
        self.team_table.removeRow(row)

    def save_team(self):
        if self.team_table.rowCount() == 0:
            QMessageBox.warning(self.window, "Empty team", "No players in team.")
            return

        team_name, ok = QInputDialog.getText(
            self.window, "Team Name", "Enter a name for your fantasy team:"
        )
        if not ok or not team_name.strip():
            return

        team_name = team_name.strip()
        total_credits = self.team_credits()

        try:
            # Insert team
            self.cur.execute(
                "INSERT INTO teams (name, total_credits, total_points) VALUES (?, ?, 0)",
                (team_name, total_credits),
            )
            team_id = self.cur.lastrowid

            # Insert team players
            for r in range(self.team_table.rowCount()):
                pid = int(self.team_table.item(r, 0).text())
                self.cur.execute(
                    "INSERT INTO team_players (team_id, player_id) VALUES (?, ?)",
                    (team_id, pid),
                )

            self.conn.commit()
            QMessageBox.information(
                self.window, "Saved", f"Team '{team_name}' saved successfully."
            )
        except sqlite3.IntegrityError:
            QMessageBox.critical(
                self.window, "Error", "Team name already exists. Choose another name."
            )
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to save team: {e}")

    # called manually at the end
    def show(self):
        self.window.show()

    def close(self):
        self.conn.close()


def main():
    app = QApplication(sys.argv)
    app_obj = FantasyApp()
    app_obj.show()
    exit_code = app.exec()
    app_obj.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
