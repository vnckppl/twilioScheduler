#! /usr/bin/env python3

# Vincent Koppelmans


# * Environment
import argparse              # Arguments
import os                    # Join file paths
import pandas as pd          # Read excel files
from crontab import CronTab  # Crontab to plan messages


# * Background
background = "This script is created to autmatically set up delivery of" \
    "reminder SMS messages to subjects participating in the EMA portion of" \
    "the UofU N(ew)EmoReg and COVID-EMA studies. This script takes an Excel" \
    "sheet with a subject's phone number, and dates+times+messages for when" \
    "this person should receive these messages."


# * Arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=background)
    parser.add_argument('excelFile',
                        help='Excel sheet with all dates, times, and messages.')
    parser.add_argument('oDir',
                        help='Output folder where messages will be stored')
    parser.add_argument('account_sid',
                        help='Twilio account string identifier (SID)')
    parser.add_argument('auth_token',
                        help='Twilio authentication token')

# ** Parse arguments
args = parser.parse_args()


# * Define messages class
class scheduleMessages:
    def __init__(self):
        # ** Store input arguments in object
        self.excelFile = args.excelFile
        self.oDir = args.oDir
        self.twilioCred = {args.account_sid: args.auth_token}

        # ** Create output folder
        os.makedirs(self.oDir, exist_ok=True)

        # ** Location of Python3
        self.myPy3 = os.popen('which python3').read().replace("\n", "")

        # ** Parse input excel file
        # The first four rows contain subject and phone number information.
        # Load this information.
        self.info = pd.read_excel(self.excelFile, header=None, nrows=4)
        self.subject = self.info[1].iloc[0]
        self.tel_from = self.info[1].iloc[1]
        self.tel_to = self.info[1].iloc[2]

        # ** Read data (date&time + message) from excel sheet
        self.data = pd.read_excel(self.excelFile, header=None, skiprows=4)
        self.data.columns = ['DateTime', 'Message']

    # * Set up cron job
    def setupCron(self):

        # ** Output folder
        self.oDirSub = os.path.join(self.oDir, self.subject)
        os.makedirs(self.oDirSub, exist_ok=True)

        # ** Dictionary for storing messages
        self.twilioMessages = {}

        # ** Loop over each line in the excel file:
        for index, row in self.data.iterrows():

            # *** Parse information
            DateTime = row['DateTime']
            Message = row['Message']

            # *** Convert date and time for message building
            DateTimeM = str(DateTime).replace("-", "").replace(":", "").replace(" ", "_")

            # *** Output filename
            # Expecting a date_time in the format of: YYYYMMDD_HHMMSS
            oFile = self.subject + "_" + DateTimeM + ".py"
            self.oFile = os.path.join(self.oDirSub, oFile)

            # *** Create Message
            self.twilioMessages[DateTimeM] = buildMessage(
                Message,
                self.tel_from,
                self.tel_to,
                self.twilioCred,
                self.oFile
            )

            # *** Convert DateTimeM to Cron Format
            minute = DateTimeM[11:13]
            hour = DateTimeM[9:11]
            day = DateTimeM[6:8]
            month = DateTimeM[4:6]

            # *** Add message job to CronTab
            # Create a cron job and remove the cron job
            # immediately after it ran. Note that upon testing
            # removing the job worked on Debian, but not OSX Mojave.
            cron = CronTab(user=True)
            job = cron.new(
                comment=f'''{self.subject}''',
                command=(
                    f'''{self.myPy3} {self.oFile}; '''
                    f'''crontab -l | grep -v {self.oFile} | crontab -'''
                ))
            job.setall(minute, hour, day, month, None)
            cron.write()


# * Build a single message
class buildMessage:
    def __init__(self, text, tel_from, tel_to, twilioCred, ofile):

        # ** Build twilio python script for an individual message
        SID = list(twilioCred.keys())[0]
        self.message = (f"""from twilio.rest import Client\n"""
                        f"""account_sid = '{SID}'\n"""
                        f"""auth_token = '{twilioCred[SID]}'\n"""
                        '\n'
                        f"""client = Client(account_sid, auth_token)\n"""
                        '\n'
                        f"""message = client.messages \\\n"""
                        f"""                .create(\n"""
                        f"""                    body='{text}',\n"""
                        f"""                    from_='+1{tel_from}',\n"""
                        f"""                    to='+1{tel_to}'\n"""
                        f"""                )\n"""
                        '\n'
                        f"""print(message.sid)\n"""
                        )

        # ** Write out twilio python script for this individual message
        with open(ofile, "w") as write_file:
            write_file.write(self.message)


# * Run Job
myObject = scheduleMessages()
myObject.setupCron()
