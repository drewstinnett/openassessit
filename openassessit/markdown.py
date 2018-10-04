from __future__ import print_function
import argparse
import jinja2
import os
import io
from operator import itemgetter
import json
import sys
import re
from collections import OrderedDict
from utils import generate_img_filename
from templates import template_path

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


class readable_dir(argparse.Action):
    """Add an option for readable directories for argparse

    https://stackoverflow.com/questions/11415570/directory-path-types-with-argparse
    """
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError(
               "readable_dir:{0} is not a valid path".format(prospective_dir)
            )
        if os.access(prospective_dir, os.R_OK):
            setattr(namespace, self.dest, prospective_dir)
        else:
            raise argparse.ArgumentTypeError(
                "readable_dir:{0} is not a readable dir".format(
                    prospective_dir)
            )


def get_args():
    example_text = '''
    examples:

    python openassessit/%(lighthouse)s -i /tmp/lighthouse-report.json -o /tmp/lighthouse-report.md

    python openassessit/%(lighthouse)s -i /tmp/lighthouse-report.json -o /tmp/lighthouse-report.md -t /your/templates

    lighthouse  https://cats.com --output=json | python openassessit/%(lighthouse)s -o lighthouse-report.md

    ''' % {'lighthouse': os.path.basename(__file__)}

    parser = argparse.ArgumentParser(epilog=example_text, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--input-file', help='Provide a the path to an input file', default=sys.stdin)
    parser.add_argument('-o', '--output-file', help='Provide a filepath where the markdown result gets written')
    parser.add_argument('-t', '--user-template-path',
                        action=readable_dir,
                        help='Provide filepath to custom user templates')
    parser.add_argument('-e', action='store_true', default=False,
                        help='Echo the output to stdout, even when using the -o option')
    return parser.parse_args()


def preprocess_data(data):

    # Get audit_refs with weights in a nice dict before full pre-processing
    metadata = {}
    for cat in data['categories']:
        for audit_ref in data['categories'][cat]['auditRefs']:
            if 'id' in audit_ref:
                metadata[audit_ref['id']] = {
                    'weight': audit_ref['weight']
                }

    for cat in data['categories']:
        data['categories'][cat]['audits'] = dict()
        for audit_ref in data['categories'][cat]['auditRefs']:
            audit = data['audits'][audit_ref['id']]
            audit['audit_template'] = '%s.md' % audit_ref['id']
            if 'displayValue' in audit and type(audit['displayValue']) is list:
                try:
                    audit['displayValue'] = audit['displayValue'][0] % tuple(audit['displayValue'][1:])
                except TypeError:
                    print(audit)
            data['categories'][cat]['audits'][audit_ref['id']] = audit

            # Add the weight right in to the audit bit, so we can easily sort
            # later
            data['categories'][cat]['audits'][audit_ref['id']]['weight'] = \
                metadata[audit_ref['id']]['weight']

    # Now that the weights are in a spot we can get, let's add a sorted list,
    # and maybe (?) in a future feature, disabled the unsorted dict
    for cat in data['categories']:
        unsorted_audits = []
        for audit_ref in data['categories'][cat]['auditRefs']:
            unsorted_audits.append(
                data['categories'][cat]['audits'][audit_ref['id']])

        # Now that it's in a nice list, let's sort it.  Reverse means highest
        # number first
        sorted_audits = sorted(unsorted_audits, key=itemgetter('weight'),
                               reverse=True)

        data['categories'][cat]['sorted_audits'] = sorted_audits

    return data


def read_input(input_file):
    if type(input_file) is str:
        with io.open(input_file, encoding='utf-8') as stream:
            return json.JSONDecoder().decode(stream.read())
    else:
        return json.JSONDecoder().decode(input_file.read())


def write_output(output_file, rendered, force_stdout=False):
    if output_file:
        with io.open(output_file, 'w', encoding='utf-8') as stream:
            stream.write(rendered)

    if force_stdout:
        print(rendered)


def main():
    args = get_args()

    paths = list()
    if args.user_template_path:
        user_template_path = args.user_template_path
        paths.append(user_template_path)
    else:
        paths.append(template_path)
    loader = jinja2.FileSystemLoader(paths)

    env = jinja2.Environment(loader=loader)

    template = loader.load(env, 'index.md')

    rendered = template.render({
        'data': preprocess_data(read_input(args.input_file)),
        'generate_img_filename': generate_img_filename,
    })

    write_output(args.output_file, rendered, force_stdout=args.e or not args.output_file)


if __name__ == '__main__':
    main()
