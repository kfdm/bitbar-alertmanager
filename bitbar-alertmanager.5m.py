#!/usr/local/bin/python3
import collections
import configparser
import logging
import os
import sys

import requests

if 'BitBar' in os.environ:
    logging.basicConfig(level=logging.WARNING)
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8')
else:
    logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAX_SHOW = 20
USER_AGENT = 'bitbar-alertmanager https://github.com/kfdm/bitbar-alertmanager'


config = configparser.ConfigParser()
config.read([os.path.expanduser('~/.config/bitbar/alertmanager.ini')])
environments = [(section, config.get(section, 'url')) for section in config.sections()]


def label(alert, label):
    if label in alert['labels']:
        if alert['labels'][label]:
            return ' {}={}'.format(label, alert['labels'][label])
    return ''


def main():
    alerts = collections.defaultdict(list)
    silenced = collections.defaultdict(int)
    ignored = collections.defaultdict(int)
    for env, url in environments:
        try:
            result = requests.get(
                '{}/api/v1/alerts'.format(url),
                headers={'user-agent': USER_AGENT}
            )
            result.raise_for_status()
        except:
            logger.error('Error querying server %s', env)
            continue
        data = result.json()['data']
        if not data:
            alerts[env] = []
            continue

        for alert in data:
            # Newer silence check
            if alert.get('status', {}).get('silencedBy'):
                logger.debug('Skipping silenced alert %s', alert['labels'])
                silenced[env] += 1
                continue
            if alert.get('status', {}).get('inhibitedBy'):
                logger.debug('Skipping silenced alert %s', alert['labels'])
                silenced[env] += 1
                continue
            if 'heartbeat' == alert['labels'].get('severity'):
                logger.debug('Skipping heartbeat alert %s', alert['labels'])
                ignored[env] += 1
                continue
            _buffer = alert['labels']['alertname']
            _buffer += label(alert, 'job')
            _buffer += label(alert, 'service')
            _buffer += label(alert, 'project')
            _buffer += ' | '
            if 'generatorURL' in alert:
                _buffer += 'href=' + alert['generatorURL']
            alerts[env].append(_buffer)

    print(':rotating_light: {}'.format(
        [len(alerts[env[0]]) for env in environments]
    ))
    for env, url in environments:
        print('---')
        print(':warning: {} Active: {} Silenced: {} Ignored: {}| href={}'.format(
            env, len(alerts[env]), silenced[env], ignored[env], url
        ))
        if len(alerts[env]) > MAX_SHOW:
            print(':bomb: Truncated error list to %s' % MAX_SHOW)
        print(u'\n'.join(sorted(alerts[env][:MAX_SHOW])))

if __name__ == '__main__':
    main()
