#!/usr/bin/python
# -*- coding: utf-8

import os
import sqlite3
import sys
import pushbullet


class CreateDatabase(object):
    GIRL_NAME = "Lány név"
    BOY_NAME = "Fiú név"

    def __init__(self, db_filename, girl_name_list, boy_name_list):
        print "Initialize new database."
        self.conn = None
        if os.path.exists(db_filename):
            print "Database file exists. Delete before creating a new one."
            return
        self.conn = sqlite3.connect(db_filename)
        self.conn.text_factory = str
        self.cur = self.conn.cursor()

        self.create_table()
        self.read_names_from_file(girl_name_list, self.GIRL_NAME)
        self.read_names_from_file(boy_name_list, self.BOY_NAME)
        print "New database %s created." % db_filename

    def create_table(self):
        self.cur.execute('CREATE TABLE IF NOT EXISTS names (name TEXT PRIMARY KEY, sex TEXT, sent INTEGER)')

    def read_names_from_file(self, file_name, sex_type):
        with open(file_name, "r") as lines:
            next(lines)  # skip first line
            for name in lines:
                utf8_name = name.decode('iso-8859-1').encode("utf-8")
                name = utf8_name.strip()
                self.cur.execute("INSERT INTO names VALUES (?, ?, 0)", (name, sex_type))
            self.conn.commit()

    def __del__(self):
        if self.conn:
            self.conn.close()


class ReadDatabase(object):
    def __init__(self, db_filename):
        self.conn = None
        self.conn = sqlite3.connect(db_filename)
        self.cur = self.conn.cursor()
        self.daily_data = []

    def read_names(self, limit=4):
        try:
            self.cur.execute('SELECT name, sex FROM names WHERE sent = 0 ORDER BY RANDOM() LIMIT ?;', (limit, ))
        except sqlite3.OperationalError as err:
            print "Wrong database.\nError: %s" % err
            sys.exit(1)
        self.daily_data = self.cur.fetchall()
        return self.collect_names()

    def collect_names(self):
        daily_names = []
        for name, sex in self.daily_data:
            daily_names.append("%s (%s)" % (name, sex))
            self.update_used_flag(name)
        return "\n".join(daily_names)

    def update_used_flag(self, name):
        self.cur.execute('UPDATE names SET sent = ? WHERE name = ?', (1, name))

    def __del__(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()


class ChildName(object):
    TODAY_NAMES = "Mai nevek:"

    def __init__(self, api_key, srv_dev_name, target_name):
        self.pb = pushbullet.PushBullet(api_key)
        self.srv = self.get_srv_device(srv_dev_name)
        self.target = self.find_contact_by_email(target_name)

    def get_srv_device(self, srv_dev_name):
        dev = self.find_device_by_name(srv_dev_name)
        if dev:
            return dev
        print "Device not found. Creating ..."
        success, dev = self.pb.new_device(srv_dev_name)
        if success:
            return dev
        raise RuntimeError("Error while creating new device.")

    def find_device_by_name(self, name):
        for dev in self.pb.devices:
            if dev.nickname == name:
                return dev

    def find_contact_by_email(self, email):
        for cont in self.pb.contacts:
            if cont.email == email:
                return cont

    def send_names(self, names):
        self.pb.push_note(self.TODAY_NAMES, names, contact=self.target)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("db_name", help="Database file")
    parser.add_argument("-n", help="Number of random selected name", type=int, default=4)
    parser.add_argument("--girls", help="Girl name list file")
    parser.add_argument("--boys", help="Boy name list file")
    args = parser.parse_args()

    DB_NAME = args.db_name

    if args.girls and args.boys:
        CreateDatabase(DB_NAME, args.girls, args.boys)
    else:
        API_KEY = ""
        SEND_TO = ""
        SEND_FROM = ""
        NUM_OF_NAMES = args.n

        db = ReadDatabase(DB_NAME)
        names = db.read_names(NUM_OF_NAMES)
        cn = ChildName(API_KEY, SEND_FROM, SEND_TO)
        cn.send_names(names)
