"""Main CLI interface for content checker."""

import argparse
import asyncio
import sys
from typing import List, Optional
import json_parser
import checker
import report_generator
import config


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check audio/video content from JSON files and generate reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all default JSON files
  python main.py

  # Check specific JSON files
  python main.py --files channels,music

  # Output format
  python main.py --output pdf
  python main.py --output csv
  python main.py --output both  # default

  # Custom timeout
  python main.py --timeout 45
        """
    )
    
    parser.add_argument(
        '--files',
        type=str,
        default='all',
        help='Comma-separated list of JSON file names (channels, music, radio, movies) or "all" (default: all)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        choices=['html'],
        default='html',
        help='Output format: html (default: html)'
    )
    
    parser.add_argument(
        '--no-open',
        action='store_true',
        help='Do not automatically open the HTML report in browser'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=None,
        help=f'Timeout per check in seconds (default: {config.DEFAULT_TIMEOUT})'
    )
    
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=3,
        help='Maximum concurrent checks (default: 3)'
    )
    
    return parser.parse_args()


def validate_file_types(file_types_str: str) -> List[str]:
    """Validate and parse file types."""
    if file_types_str.lower() == 'all':
        return list(config.JSON_URLS.keys())
    
    file_types = [ft.strip() for ft in file_types_str.split(',')]
    valid_types = list(config.JSON_URLS.keys())
    
    invalid_types = [ft for ft in file_types if ft not in valid_types]
    if invalid_types:
        print(f"Warning: Invalid file types: {', '.join(invalid_types)}")
        print(f"Valid types are: {', '.join(valid_types)}")
        sys.exit(1)
    
    return file_types


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Parse file types
    file_types = validate_file_types(args.files)
    print(f"Checking files: {', '.join(file_types)}")
    
    # Fetch and parse JSON files
    print("\nFetching JSON files...")
    content_items = json_parser.parse_all_json_files(file_types)
    
    if not content_items:
        print("No content items found. Exiting.")
        sys.exit(1)
    
    print(f"\nTotal items to check: {len(content_items)}")
    
    # Initialize checker
    content_checker = checker.ContentChecker(
        timeout=args.timeout,
        max_concurrent=args.max_concurrent
    )
    
    # Check all items
    results = await content_checker.check_all(content_items)
    
    # Get summary
    summary = content_checker.get_summary()
    
    # Print summary
    print("\n" + "="*60)
    print("CHECK SUMMARY")
    print("="*60)
    print(f"Total Items: {summary['total']}")
    print(f"Working: {summary['working']}")
    print(f"Broken: {summary['broken']}")
    print("\nBy Type:")
    for type_name, type_stats in summary['by_type'].items():
        print(f"  {type_name.capitalize()}: {type_stats['working']}/{type_stats['total']} working")
    print("="*60)
    
    # Generate reports
    print("\nGenerating reports...")
    report_gen = report_generator.ReportGenerator()
    generated_files = report_gen.generate_reports(results, summary, args.output, auto_open=not args.no_open)
    
    print(f"\n✓ Check complete! Generated {len(generated_files)} report(s).")
    for file in generated_files:
        print(f"  - {file}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
