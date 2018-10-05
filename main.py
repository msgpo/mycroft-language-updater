import sys
import os
from os.path import join, basename, exists
from glob import glob
from datetime import date
from requests import get

import polib
from github_actions import get_work_repos, create_work_dir, create_or_edit_pr

DEFAULT_BRANCH = '18.08'
SKILLS_URL = ('https://raw.githubusercontent.com/MycroftAI/mycroft-skills/'
              '{}/.gitmodules')


def get_skill_repos(branch=None):
    """ Fetches the skill list from the mycroft-skills repo and returns
        a dict mapping paths to urls

        Arguments:
            branch: branch of the repo to use

        Returns: dict with path-url pairs
    """
    branch = branch or DEFAULT_BRANCH
    response = get(SKILLS_URL.format(branch))
    skills = response.text.split('\n')

    d = {}
    key = None
    for l in skills:
        if 'path = ' in l:
            key = l.split(' = ')[1].strip()
        elif key and 'url = ' in l:
            d[key] = l.split(' = ')[1].strip()
            key = None
        else:
            key = None
    return d


def download_lang(lang):
    # TODO
    # build url for language code

    # use wget module to download

    # use zip to unpack

    return path # Path to directory with po_files


def is_translated(path):
    """ Checks if all files in the translation has at least one translation.

    Arguments:
        path (str): path to po-file

    Returns: True if all files in translation has at least one translation,
             otherwise False.
    """
    po = polib.pofile(path)
    files = []
    for e in po:
        files += [f[0] for f in e.occurrences]
    all_files = sorted(set(files))
    translated_entities = [e for e in po if e.translated()]
    files = []
    for e in translated_entities:
        files += [f[0] for f in e.occurrences]
    translated_files = sorted(set(files))

    return translated_files == all_files


def parse_po_file(path):
    """ Create dictionary with translated files as key containing
    the file content as a list.

    Arguments:
        path: path to the po-file of the translation

    Returns:
        Dictionary mapping files to translated content
    """
    out_files = {}  # Dict with all the files of the skill
    # Load the .po file
    po = polib.pofile(path)

    for entity in po:
        for out_file, _ in entity.occurrences:
            f = out_file.split('/')[-1] # Get only the filename
            content = out_files.get(f, [])
            content.append(entity.msgstr)
            out_files[f] = content

    return out_files


def insert_translation(path, translation):
    for filename in translation:
        with open(join(path, filename), 'w+') as f:
            f.writelines([l + '\n' for l in translation[filename]])


pootle_langs = {
    'sv-se': 'sv',
    'de-de': 'de'
}


def main():
    skill_repos = get_skill_repos()
    
    for skill in skill_repos:
        # Get repo information
        skill_url = skill_repos[skill]
        # Get git repo and github connections
        fork, upstream = get_work_repos(skill_url)
        work = create_work_dir(upstream, fork) # local clone

        for lang in pootle_langs:
            # Build po-file path
            f = (join(pootle_langs[lang] + '-mycroft-skills',
                      pootle_langs[lang],
                      'mycroft-skills',
                      skill + '-' + pootle_langs[lang] + '.po'))
            if not exists(f) or not is_translated(f):
                continue
            print('Processing {}'.format(f))
            translation = parse_po_file(f)
            # Modify repo
            # Checkout new branch
            branch = 'translate-' + str(date.today())
            work.checkout('-b', branch)

            if 'locale' in os.listdir(work.tmp_path):
                path = join('locale', lang)
                if not exists(join(work.tmp_path,path)):
                    os.mkdir(join(work.tmp_path, path))
                else:
                    work.rm(join(path, '*'))  # Remove all files
                # insert new translations
                insert_translations(join(work.tmp_path, path), translations)
                work.add(join(path, '*'))  # add the new files
            else:
                # handle dialog directory
                path = join('dialog', lang)
                if not exists(join(work.tmp_path,path)):
                    os.mkdir(join(work.tmp_path, path))
                else:
                    work.rm(join(path, '*'))  # Remove all files
                insert_translation(join(work.tmp_path, path),
                    {k: translation[k] for k in translation if
                        k.endswith('.dialog')})
                insert_translation(join(work.tmp_path, path),
                    {k: translation[k] for k in translation if
                        k.endswith('.list')})
                work.add(join(path, '*'))  # add the new files
                # handle vocab directory
                path = join('vocab', lang)
                if not exists(join(work.tmp_path,path)):
                    os.mkdir(join(work.tmp_path, path))
                else:
                    work.rm(join(path, '*'))  # Remove all files
                insert_translation(join(work.tmp_path, path),
                    {k: translation[k] for k in translation if
                        k.endswith('.intent')})
                insert_translation(join(work.tmp_path, path),
                    {k: translation[k] for k in translation if
                        k.endswith('.voc')})
                insert_translation(join(work.tmp_path, path),
                    {k: translation[k] for k in translation if
                        k.endswith('.entity')})
                work.add(join(path, '*'))  # add the new files
                # Handle regex dir
                path = join('regex', lang)
                if exists(join(work.tmp_path, 'regex')):
                    if not exists(join(work.tmp_path,path)):
                        os.mkdir(join(work.tmp_path, path))
                    else:
                        work.rm(join(path, '*'))  # Remove all files
                    insert_translation(join(work.tmp_path, path),
                        {k: translation[k] for k in translation if
                            k.endswith('.rx')})
        #TODO CHECK git diff to determine if anything has changed
        # Commit
        work.commit('-m', 'Update translations')
        # Push branch to fork
        work.push('-f', 'work', branch)
        # Open PR
        create_or_edit_pr(branch, upstream)
        work.tmp_remove()

if __name__ == '__main__':
    main()
