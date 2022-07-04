import os
import argparse
import pandas as pd
from src.log_preprocess import get_templates_using_drain3, get_logs_df, get_structured_logs_df
from src.utils import common_logger
from config import settings


def main():
    # argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--system', help="System name", type=str, default=None)
    parser.add_argument('-it', '--identify_templates', help="Identify templates (default: false)",
                        action='store_true', default=False)
    parser.add_argument('-mlt', '--merge_logs_and_templates', help="Merge logs and templates",
                        action='store_true', default=False)
    parser.add_argument('-dm', '--drop_message', help="Drop messages in the structured log",
                        action='store_true', default=False)
    args = parser.parse_args()

    logger, timestamp = common_logger('LogPrep')
    print(f'system={args.system}, '
          f'identify_templates={args.identify_templates}, '
          f'merge_logs_and_templates={args.merge_logs_and_templates}')
    logger.info(f'system={args.system}, '
                f'identify_templates={args.identify_templates}, '
                f'merge_logs_and_templates={args.merge_logs_and_templates}')

    if args.system is None:
        systems = settings.keys()
    else:
        systems = [args.system]

    summary = []
    for system in systems:
        print('-'*80)
        print(f'{system}')
        logger.info(f'system={system}')

        if args.identify_templates:
            num_templates = get_templates_using_drain3(
                system=system,
                log_dir=settings[system]['log_dir'],
                file_ext=settings[system]['file_ext'],
                log_format=settings[system]['log_format'],
                output_dir=os.path.join('output', system),
                drop_message=args.drop_message
            )
            summary.append([system, num_templates])

        elif args.merge_logs_and_templates:
            # merge logs (either unstructured or structured) and templates (just a list of templates in .csv)

            if 'log_split_keyword' in settings[system].keys():
                log_split_keyword = settings[system]['log_split_keyword']
            else:
                log_split_keyword = None

            structured_logs_df, templates_df = get_structured_logs_df(
                system=system,
                log_dir=settings[system]['log_dir'],
                file_ext=settings[system]['file_ext'],
                log_format=settings[system]['log_format'],
                template_dir=settings[system]['template_dir'],
                output_dir=os.path.join('output', system),
                log_split_keyword=log_split_keyword
            )
            summary.append([system, len(templates_df), len(structured_logs_df)])

        else:
            # simply convert unstructured logs into structured one (.csv)

            if 'log_split_keyword' in settings[system].keys():
                log_split_keyword = settings[system]['log_split_keyword']
            else:
                log_split_keyword = None

            logs_df = get_logs_df(
                system=system,
                log_dir=settings[system]['log_dir'],
                file_ext=settings[system]['file_ext'],
                log_format=settings[system]['log_format'],
                log_split_keyword=log_split_keyword
            )

            # # (level_filtering) keep specified levels only
            # level_filtering = ['I', 'INFO', 'info', 'Info']
            # if 'level' in logs_df.columns:
            #     logger.info(f'List of levels for level-filtering: {level_filtering}')
            #     print(f'List of levels for level-filtering: {level_filtering}')
            #     logs_dfs = list()
            #     for level in level_filtering:
            #         logs_dfs.append(logs_df[logs_df.level == level])
            #     logs_df = pd.concat(logs_dfs)
            #     assert (len(logs_df) > 0)

            # save templates
            output_dir = os.path.join('output', system)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            logs_df.to_csv(os.path.join('output', system, f'{system}.csv'), index=False)
            summary.append([system, len(logs_df)])

    if args.identify_templates:
        print('\n=== Template Identification Summary ===')
        summary_df = pd.DataFrame(summary, columns=['system', 'templates'])

    elif args.merge_logs_and_templates:
        print('\n=== Structured Log Summary ===')
        summary_df = pd.DataFrame(summary, columns=['system', 'templates', 'log messages'])

    else:
        print('\n=== Preprocessed Log Summary (No Template) ===')
        summary_df = pd.DataFrame(summary, columns=['system', 'log messages'])

    print(summary_df)
    logger.info('run_preprocess: ends without errors')


if __name__ == '__main__':
    main()
