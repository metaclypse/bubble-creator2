#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
import datetime
import sys
import argparse
import logging
import shutil
import tqdm
from webptools import dwebp
from media_extraction import ogg_to_pdf, thumbnail_from_video


class BubbleCreator(object):
    def __init__(self):
        self.emoji_data = None
        self.self_user_id = None
        self.data_path = None
        self.destination_path = None
        self.json_file_path = None
        self.config_file_path = None
        self.emoji_images_path = None
        self.bg_path = None

        self.template_path = 'template'

    def clean_string_for_tex(self, input_string):
        output_string = input_string

        # replace emojis with images
        for emoji_character in self.emoji_data.keys():
            # check if string contains current emoji
            if emoji_character in output_string:
                # check if we have that emoji as an image file
                file_name = os.path.join(self.emoji_images_path,
                                         self.emoji_data[emoji_character].replace('+', '').replace('U', 'u').replace(' ', ''))
                if os.path.isfile(file_name + '.png') or os.path.isfile(file_name + '.pdf'):
                    output_string = output_string.replace(emoji_character, self.tex_cmd_emoji(self.emoji_data[emoji_character]))
                else:
                    # command = r'\includegraphics[width=.1\textwidth]{' + 'missing-emoji.pdf' + '}'
                    # output_string = output_string.replace(emoji_character, command)
                    output_string = '(emoji picture missing: {})'.format(file_name)

        # replace latex symbols with escaped symbols
        latex_bad = {
            '_': r'\_',
            '^': r'\^{}',
            '℃': r'$^{\circ}$C',
            '"': "``",
            '#': r'\#',
            '%': r'\%',
            '\ufe0f': '',
            '\u1f3fe': '',
            '&': r'\&'  # TODO complete
        }
        for emoji_character in latex_bad.keys():
            output_string = output_string.replace(emoji_character, latex_bad[emoji_character])

        # print('cleaned: ' + input_string + ' --> ' + output_string)
        return output_string

    # gives the includegraphics latex command with the right emoji path for an utf emoji code
    def tex_cmd_emoji(self, code):
        file_name = 'emoji/' + code.replace('+', '').replace('U', 'u')
        command = r'\includegraphics[width=.1\textwidth]{' + file_name + '}'
        return command

    def format_seconds(self, s):
        seconds = s
        minutes = int(seconds / 60)
        seconds -= minutes * 60
        return str(minutes).zfill(2) + ':' + str(seconds).zfill(2)

    def format_url(self, unbreakable_link):
        # problem: Links are counted as long words in LaTeX
        # solution: We add the \- command after every character, that allows a line break
        breakable_link = ''
        distance_to_backslash = 0  # if we find a backslash, we only insert \- a bit later again
        for j in range(len(unbreakable_link)):
            if j == 0:
                breakable_link += unbreakable_link[j]
            else:
                if unbreakable_link[j] == '\\':
                    breakable_link += unbreakable_link[j]
                    distance_to_backslash = 4
                else:
                    if distance_to_backslash > 0:
                        if unbreakable_link[j] == '-':
                            breakable_link += '\hyph{}'
                        else:
                            breakable_link += unbreakable_link[j]
                        distance_to_backslash -= 1
                    else:
                        if unbreakable_link[j] == '-':
                            breakable_link += '\hyph{}'
                        else:
                            breakable_link += r'\-' + unbreakable_link[j]

        return breakable_link

    def format_voice_message(self, p_message):
        curr_file = p_message.get('file', '')
        message_tex_content = r'\includegraphics[width=.15\textwidth]{playbutton.pdf} '
        if 'file' in p_message:
            ogg_path = os.path.join(self.data_path, curr_file)
            voice_graph_path = os.path.join(self.destination_path, 'voice_graphs')
            if os.path.isfile(ogg_path):
                if not os.path.isdir(voice_graph_path):
                    os.mkdir(voice_graph_path)
                fn = ogg_to_pdf(ogg_path, voice_graph_path)
                rfn = 'voice_graphs' + os.path.pathsep + os.path.basename(fn)
                message_tex_content += r'\includegraphics[width=.5\textwidth]{' + fn + r'} \\'
        message_tex_content += r'Voice Message'
        if 'duration_seconds' in p_message:
            formatted_duration = self.format_seconds(int(p_message['duration_seconds']))
            message_tex_content += ' (' + formatted_duration + ')'

        return message_tex_content

    def prepare(self, message_data):
        # collect users from chat data
        global self_user_id
        users = []
        user_names = []

        for m in message_data:
            if 'from_id' in m:
                if not m['from_id'] in users:
                    users.append(m['from_id'])
                    if m['from'] is None:
                        user_names.append('Unknown User')
                    else:
                        user_names.append(m['from'])

            elif 'actor_id' in m:
                if not m['actor_id'] in users:
                    users.append(m['actor_id'])
                    if m['actor'] is None:
                        user_names.append('Unknown User')
                    else:
                        user_names.append(m['actor'])

        # select user who is 'you'
        print('The following users have been found in the chat:')
        for i in range(len(users)):
            print('{}: {} ({})'.format(i, user_names[i], users[i]))

        choice = -1
        choice = 0  # fixme: this line is only for testing!
        while not choice in range(len(users)):
            try:
                choice = int(input('Select the user that will be on the right side: '))
            except ValueError as v:
                print('Please enter a valid number between {} and {}.'.format(0, len(users) - 1))

        print('Selected {} ({})'.format(user_names[choice], users[choice]))
        self_user_id = users[choice]

    def process_message(self, p_message):
        curr_from_id = p_message.get('from_id', '')
        curr_forwarded_from = p_message.get('forwarded_from', '')
        curr_date = str(p_message.get('date', 'yyyy-mm-ddThh:mm:ss'))[11:-3]
        curr_text = p_message.get('text', 'Message text could not be retrieved.')
        curr_photo = p_message.get('photo', '')
        curr_file = p_message.get('file', '')
        curr_media_type = p_message.get('media_type', '')

        message_tex_content = ''

        if curr_forwarded_from != '':
            message_tex_content += r'\smallextra{Forwarded from ' \
                                   + curr_forwarded_from \
                                   + r'} \vspace{-.75\baselineskip}' \
                                   + '\n'

        # If a link or a call was sent, the text of the message is a list. If so, we check the contents:
        if isinstance(curr_text, list) and curr_text:
            for element in curr_text:
                if isinstance(element, dict):
                    message_type = element['type']
                    if message_type == 'link':
                        unbreakable_link = self.clean_string_for_tex(str(element['text']))
                        breakable_link = self.format_url(unbreakable_link)
                        message_tex_content += '\\begin{minipage}{\\textwidth}\\urlStyle{' + breakable_link + '}\\end{minipage}'
                        # message_tex_content += '\\url{' + str(element['text']) + '}'
                        # message_tex_content += r'\href{' + str(element['text']) + '}'
                    else:
                        message_tex_content += 'Unhandled message type: ' + message_type
                else:
                    message_tex_content += str(element)

        elif isinstance(curr_text, dict) and curr_text:
            ct_type = curr_text.get('type', '')
            ct_text = curr_text.get('text', '')

        elif curr_media_type == 'voice_message' and 'duration_seconds' in p_message:
            message_tex_content += self.format_voice_message(p_message)

        elif (curr_media_type == 'animation' or curr_media_type == 'video_file') \
                and ('thumbnail' in p_message or 'file' in p_message):

            if 'thumbnail' in p_message:
                source_thumbnail_path = os.path.join(self.data_path, p_message.get('thumbnail'))
                message_tex_content += r'\includegraphics[width=.5\textwidth]{' + source_thumbnail_path + r'} '
            elif 'file' in p_message:
                # If there is a file but not a thumbnail, we have to create the thumbnail ourselves.
                target_thumbnail_folder = os.path.join(self.destination_path, 'thumbnails')
                if not os.path.exists(target_thumbnail_folder):
                    os.mkdir(target_thumbnail_folder)

                source_file_path = os.path.join(self.data_path, curr_file)
                target_thumbnail_path = os.path.join(target_thumbnail_folder,
                                                     os.path.basename(source_file_path) + '.jpg')
                thumbnail_from_video(source_file_path, target_thumbnail_path)

                message_tex_content += r'\includegraphics[width=.5\textwidth]{' + target_thumbnail_path + r'} '

            if 'duration_seconds' in p_message:
                formatted_duration = self.format_seconds(int(p_message['duration_seconds']))
                message_tex_content += r'\ \\ Video (' + formatted_duration + r')'

        elif curr_media_type == 'sticker' and 'thumbnail' in p_message:
            # Thumbnails are in WEBP format (despite the file ending). We have to convert to JPEG.
            source_thumbnail_path = os.path.join(self.data_path, p_message.get('thumbnail'))
            target_thumbnail_folder = os.path.join(self.destination_path, 'stickers')
            target_thumbnail_path = os.path.join(target_thumbnail_folder,
                                                 os.path.basename(source_thumbnail_path)[:-3] + 'png')

            if not os.path.isdir(target_thumbnail_folder):
                os.mkdir(target_thumbnail_folder)

            logging.debug(dwebp(input_image='"' + source_thumbnail_path + '"',
                                output_image='"' + target_thumbnail_path + '"',
                                option="-o",
                                logging="-v"))

            message_tex_content += r'\includegraphics[width=.4\textwidth]{' + target_thumbnail_path + r'} '

        else:
            # process photo
            if curr_photo != '':
                photo_path = os.path.join(self.data_path, curr_photo)
                message_tex_content += r'\includegraphics[width=.75\textwidth]{' + photo_path + '}\\\\ '
            # process file
            elif curr_file != '':
                file_name = os.path.basename(os.path.join(self.data_path, curr_file))
                file_name = self.clean_string_for_tex(file_name)
                message_tex_content += r'\includegraphics[width=.15\textwidth]{file.pdf} \textbf{' + file_name + r'}'
                if curr_text != '':
                    message_tex_content += r'\\'
            message_tex_content += self.clean_string_for_tex(str(curr_text))

        return message_tex_content

    def convert(self, message_data, compile_after_convert=False):
        max_message_per_file = 1000

        structured_messages = []  # Messages grouped by sender.

        # Go through all messages in the list:
        # for curr_message in message_data:
        for j in tqdm.tqdm(range(len(message_data)), desc='Step 1 (Converting)', file=sys.stdout):
            curr_message = message_data[j]
            # Each curr_message is a dict object.
            curr_from_id = curr_message.get('from_id', '')
            curr_date = str(curr_message.get('date', 'yyyy-mm-ddThh:mm:ss'))[11:-3]

            message_tex_content = self.process_message(curr_message)

            if curr_from_id == self_user_id:
                date_command = '\\rmsgtime{' + str(curr_date) + '}'
            else:
                date_command = '\\lmsgtime{' + str(curr_date) + '}'

            # The following code segment groups message contents together by sender. This makes it look prettier in the
            # final file, since like this, the edges of the grouped messages 'point' towards the sender.
            if not structured_messages:
                first_entry = {
                    'sender': curr_from_id,
                    'message': message_tex_content + date_command,
                    'date': datetime.datetime.strptime(str(curr_message['date']), '%Y-%m-%dT%H:%M:%S')
                }
                structured_messages.append(first_entry)
            else:
                l = len(structured_messages) - 1
                if structured_messages[l]['sender'] == curr_from_id:
                    structured_messages[l]['message'] += u'\n\n' + message_tex_content + date_command
                else:
                    new_entry = {
                        'sender': curr_from_id,
                        'message': message_tex_content + date_command,
                        'date': datetime.datetime.strptime(str(curr_message['date']), '%Y-%m-%dT%H:%M:%S')
                    }
                    structured_messages.append(new_entry)

        final_strings = []
        for j in range(int(len(structured_messages) / max_message_per_file) + 1):  # add 1 to be sure
            final_strings.append(u'')

        curr_part = 0
        last_date = datetime.datetime(1900, 1, 1, 0, 0, 0)

        # for curr_message in structured_messages:
        for j in tqdm.tqdm(range(len(structured_messages)), desc='Step 2 (Making bubbles)', file=sys.stdout):
            curr_message = structured_messages[j]
            d = curr_message['date']
            if last_date.date() != d.date():
                final_strings[curr_part] += '\\datebubble{' + '{}.{}.{}'.format(d.day, d.month, d.year) + '}\n'
                last_date = curr_message['date']

            if curr_message['sender'] == self_user_id:
                final_strings[curr_part] += u'\\begin{rightbubbles}\n' \
                                            + curr_message['message'] \
                                            + u'\n\\end{rightbubbles}\n'
            else:
                final_strings[curr_part] += u'\\begin{leftbubbles}\n' \
                                            + curr_message['message'] \
                                            + u'\n\\end{leftbubbles}\n'

        with open('template/template.tex', 'r') as f:
            template = f.read()

        bg_decl_placeholder = '%BACKGROUND_DECLARATION_PLACEHOLDER'
        if self.bg_path is None:
            logging.debug('No background image set.')
            template = template.replace(bg_decl_placeholder, '')
        elif isinstance(self.bg_path, str):
            bg_declaration = r'\AddToShipoutPictureBG{\includegraphics[height=\paperheight]{' + self.bg_path + r'}}'
            template = template.replace(bg_decl_placeholder, bg_declaration)

        chat_data_placeholder = '%CHAT_DATA_PLACEHOLDER'
        template_parts = template.split(chat_data_placeholder)

        if compile_after_convert:
            os.chdir(self.destination_path)

        max_digits = len(str(len(final_strings)))
        for j in tqdm.tqdm(range(len(final_strings)), desc='Step 3 (Saving LaTeX)', file=sys.stdout):
            curr_file_name = 'test-out-' + str(j).zfill(max_digits) + '.tex'
            dest = os.path.join(self.destination_path, curr_file_name)

            logging.debug('Writing {}th file to {}'.format(j, dest))
            with open(dest, 'w') as f:
                f.write(template_parts[0] + final_strings[j] + template_parts[1])

            # Compiling the LaTeX file via system command:
            if compile_after_convert:
                os.system('pdflatex ' + dest)

    def run(self, compile=False):
        # derive various paths from the source / destination paths
        self.json_file_path = os.path.join(self.data_path, 'result.json')
        self.config_file_path = os.path.join(self.data_path, 'bc2-config.json')
        self.emoji_images_path = os.path.join(self.destination_path, 'emoji')

        # check if source path contains the JSON file, if not exit
        if not os.path.isfile(self.json_file_path):
            logging.error('result.json not found in ' + self.data_path)
            sys.exit(1)

        # get emoji data from auxiliary file
        with open('./emoji-codes.json') as ecf:
            self.emoji_data = json.load(ecf)

        # create destination path if it doesn't exist
        if not os.path.isdir(self.destination_path):
            logging.debug('Destination folder was created: ' + self.destination_path)
            os.mkdir(self.destination_path)

        # check if emoji path exists:
        if not os.path.isdir(self.emoji_images_path):
            logging.warning('Emoji image folder does not exist. Will revert to placeholder.')

        # copy required template files into destination path:
        assets = ['missing-emoji.pdf', 'playbutton.pdf', 'file.pdf']
        for a in assets:
            asset_src_path = os.path.join(self.template_path, a)
            asset_dst_path = os.path.join(self.destination_path, a)
            if not os.path.isfile(asset_dst_path):
                shutil.copy(asset_src_path, asset_dst_path)

        # open the JSON file, read the data
        with open(self.json_file_path, 'r') as f:
            string_data = f.read()
        data = json.loads(string_data)
        message_data = data.get('messages', '')

        # step 1: preparation
        self.prepare(message_data)

        # step 2: generation
        self.convert(message_data, compile_after_convert=compile)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # program argument parsing
    arg_parser = argparse.ArgumentParser(description='Generates (a) working LaTeX file(s) to make a nice document out '
                                                     'of saved Telegram chats.')
    arg_parser.add_argument("source", help="Path of the directory containing the exported chat data")
    arg_parser.add_argument("target", help="Target directory for the LaTeX files (will be created if not existing)")
    arg_parser.add_argument("-a", '--autocompile', action='store_true', help="Compile automatically after generation")
    args = arg_parser.parse_args()

    bc = BubbleCreator()

    # source and destination from arguments
    bc.data_path = args.source
    bc.destination_path = args.target
    bc.bg_path = 'bg3.png'

    bc.run(compile=args.autocompile)