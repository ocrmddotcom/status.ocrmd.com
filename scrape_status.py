import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import sys
import os
import re
import argparse

def sanitize_service_name_for_filename(service_name_str):
    if not isinstance(service_name_str, str):
        service_name_str = str(service_name_str)
    name = re.sub(r'[\s/\\:]+', '_', service_name_str)
    name = re.sub(r'[<>"/\\|?*\x00-\x1F]', '', name)
    name = name.strip('_')
    if not name:
        return "default_service"
    return name

def create_badge_svg(service_display_text, status, color):
    height = 28
    font_size_service = 14
    font_size_status = 13
    font_family = "'Segoe UI', Helvetica, Arial, sans-serif"
    rounded_radius = 6
    badge_bg_color_start = "#4A4A4A"
    badge_bg_color_end = "#333333"
    text_color = "#FFFFFF"
    separator_color = "#555555"
    base_width_per_char_service = 9
    base_width_per_char_status = 8
    padding_horizontal = 12
    gap_circle_text = 6
    circle_radius = 5

    status_display_text = status.replace('_', ' ').strip()
    service_display_text_str = str(service_display_text)

    service_text_width = len(service_display_text_str) * base_width_per_char_service
    status_text_width = len(status_display_text) * base_width_per_char_status
    status_content_actual_width = (
        (circle_radius * 2) + gap_circle_text + status_text_width
    )
    service_section_width = service_text_width + (2 * padding_horizontal)
    status_section_width = status_content_actual_width + (
        2 * padding_horizontal
    )
    min_service_width = max(
        60,
        len("Service") * base_width_per_char_service + 2 * padding_horizontal,
    )
    min_status_width = max(
        50,
        (circle_radius * 2)
        + gap_circle_text
        + (len("OK") * base_width_per_char_status)
        + 2 * padding_horizontal,
    )
    service_section_width = max(service_section_width, min_service_width)
    status_section_width = max(status_section_width, min_status_width)
    total_width = service_section_width + status_section_width
    service_text_x = service_section_width / 2
    service_text_y = height / 2 + 1
    separator_x = service_section_width
    status_elements_start_x = separator_x + padding_horizontal
    circle_center_x = status_elements_start_x + circle_radius
    circle_center_y = height / 2
    status_text_x_start = circle_center_x + circle_radius + gap_circle_text
    status_text_y = height / 2 + 1

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="{height}" style="background: transparent;">
  <defs>
    <linearGradient id="badgeGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{badge_bg_color_start};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{badge_bg_color_end};stop-opacity:1" />
    </linearGradient>
  </defs>
  <g>
    <rect width="{total_width}" height="{height}" rx="{rounded_radius}" ry="{rounded_radius}"
          fill="url(#badgeGradient)" />
    <line x1="{separator_x}" y1="{height * 0.2}" x2="{separator_x}" y2="{height * 0.8}"
          stroke="{separator_color}" stroke-width="1" stroke-opacity="0.5" />
    <text x="{service_text_x}" y="{service_text_y}" fill="{text_color}" text-anchor="middle"
          font-family="{font_family}" font-size="{font_size_service}" font-weight="500" dominant-baseline="middle">
      {service_display_text_str}
    </text>
    <circle cx="{circle_center_x}" cy="{circle_center_y}" r="{circle_radius}" fill="{color}" />
    <text x="{status_text_x_start}" y="{status_text_y}" fill="{text_color}" text-anchor="start"
          font-family="{font_family}" font-size="{font_size_status}" font-weight="400" dominant-baseline="middle">
      {status_display_text}
    </text>
  </g>
</svg>"""
    return svg_content.strip()

def get_status_color(status):
    """Maps status text to a color."""
    status_lower = status.lower()
    if 'healthy' in status_lower or 'operational' in status_lower or 'ok' in status_lower:
        return '#4c1' # Green
    elif 'degraded' in status_lower or 'performance' in status_lower or 'minor' in status_lower:
        return '#fe7d37' # Orange
    elif 'outage' in status_lower or 'down' in status_lower or 'major' in status_lower or 'unavailable' in status_lower or 'failed' in status_lower:
        return '#e05d44' # Red
    elif 'maintenance' in status_lower or 'scheduled' in status_lower:
        return '#007ec6' # Blue
    elif 'investigating' in status_lower or 'monitoring' in status_lower:
         return '#f1a33c' # Yellow/Orange
    else:
        return '#9f9f9f' # Grey (Unknown/Other)

def clean_service_name(service_name, status=None):
    """Removes status information from service name."""
    # List of common status terms to remove from service names
    status_terms = [
        'healthy', 'operational', 'ok', 'all systems operational', 
        'degraded performance', 'partial outage', 'major outage',
        'under maintenance', 'investigating', 'monitoring', 'failed',
        'unavailable', 'down'
    ]
    
    # If we know the actual status, add it to the list of terms to remove
    if status:
        status_terms.append(status.lower())
    
    cleaned_name = service_name
    for term in status_terms:
        # Try to remove the term from the end of the service name
        pattern = r'\s*[-:]?\s*' + re.escape(term) + r'$'
        cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
        
        # Also try to remove it with parentheses or brackets
        cleaned_name = re.sub(r'\s*\([^)]*' + re.escape(term) + r'[^)]*\)', '', cleaned_name, flags=re.IGNORECASE)
        cleaned_name = re.sub(r'\s*\[[^\]]*' + re.escape(term) + r'[^\]]*\]', '', cleaned_name, flags=re.IGNORECASE)
    
    # Trim any trailing special characters and whitespace
    cleaned_name = re.sub(r'[-:,\s]+$', '', cleaned_name)
    
    # Default to "Service" if name becomes empty
    if not cleaned_name.strip():
        return "Service"
    
    return cleaned_name.strip()

async def scrape_status_page(url, executable_path=None):
    services = {}
    browser = None
    try:
        async with async_playwright() as p:
            browser_options = {"headless": True}
            if executable_path:
                 browser_options["executable_path"] = executable_path
                 print(f"Using browser binary at: {executable_path}")
            else:
                 print("Using Playwright's default browser installation.")
            browser_options['args'] = ['--no-sandbox', '--disable-setuid-sandbox']
            browser = await p.chromium.launch(**browser_options)
            page = await browser.new_page()
            print(f"Navigating to {url}")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            service_selector = 'div[class*="MuiAccordion-root"]'
            try:
                await page.wait_for_selector(service_selector, state='visible', timeout=45000)
                print("Service elements found.")
            except Exception as e:
                print(f"Error waiting for service elements on {url}: {e}")
                print("Attempting to scrape available content anyway.")
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            accordion_items = soup.select(service_selector)
            if not accordion_items:
                 print(f"Warning: No accordion items found using selector '{service_selector}'.")
                 return services
            for item in accordion_items:
                try:
                    name_element = item.select_one('.MuiAccordionSummary-content div, .MuiAccordionSummary-content span[class*="MuiTypography"]')
                    service_key_from_page = name_element.get_text(strip=True) if name_element else 'Unknown Service'
                    status_element = item.select_one('.MuiAccordionSummary-content div:nth-child(2), .MuiAccordionSummary-content span')
                    status_value = status_element.get_text(strip=True) if status_element else 'Unknown'
                    if status_value == 'Unknown':
                         item_text = item.get_text()
                         status_matches = re.findall(r'(Operational|Healthy|OK|All Systems Operational|Degraded Performance|Partial Outage|Major Outage|Under Maintenance|Investigating|Monitoring|Failed)', item_text, re.IGNORECASE)
                         if status_matches:
                              status_value = status_matches[0]
                    if service_key_from_page and status_value and status_value.lower() not in ['unknown', 'unknown service']:
                        status_value = re.sub(r'\s+', ' ', status_value).strip()
                        if status_value.lower() == service_key_from_page.lower():
                             print(f"Skipping service '{service_key_from_page}' as status text matches service name.")
                             continue
                        services[service_key_from_page] = status_value
                except Exception as e:
                    print(f"Error processing an accordion item during parsing: {e}")
    except Exception as e:
        print(f"A critical error occurred during Playwright scraping of {url}: {e}")
        if not services:
             services['Scraping Status'] = 'Execution Error'
    finally:
        if browser:
            await browser.close()
    return services

async def run_scraper_with_timeout(url, executable_path, timeout_seconds):
    try:
        print(f"Starting scrape_status_page with an overall timeout of {timeout_seconds} seconds.")
        services_status = await asyncio.wait_for(
            scrape_status_page(url, executable_path),
            timeout=timeout_seconds
        )
        return services_status
    except asyncio.TimeoutError:
        print(f"Error: Scraping timed out after {timeout_seconds} seconds for {url}")
        return {'Scraping Status': 'Timeout Error'}
    except Exception as e:
         print(f"An unexpected error occurred during the timed scraping process: {e}")
         return {'Scraping Status': 'Unexpected Error'}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape service statuses or generate a debug SVG badge.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status-url", help="The URL of the status page to scrape.")
    group.add_argument("--debug-badge", nargs=2, metavar=('SERVICE_NAME', 'STATUS'),
                       help="Generate a single badge for debugging. Provide service name and status.")

    parser.add_argument("--executable-path", help="Optional: Path to browser executable (for URL scraping).", default=None)
    parser.add_argument("--timeout", type=int, default=120, help="Overall scraping timeout (sec) (for URL scraping).")

    args = parser.parse_args()
    output_dir = "status_badges"
    os.makedirs(output_dir, exist_ok=True)

    if args.debug_badge:
        service_key_original = args.debug_badge[0]
        status_value = args.debug_badge[1]
        print(f"Debug mode: Generating badge for Service='{service_key_original}', Status='{status_value}'")

        # Clean the service name to remove any status information
        service_display_name_for_badge = clean_service_name(service_key_original, status_value)
        service_display_name_for_badge = service_display_name_for_badge.replace('_', ' ')
        
        filename_base = sanitize_service_name_for_filename(service_display_name_for_badge)
        badge_filename = os.path.join(output_dir, f"{filename_base}.svg")
        color = get_status_color(status_value)
        svg_content = create_badge_svg(service_display_name_for_badge, status_value, color)

        try:
            with open(badge_filename, "w", encoding="utf-8") as f:
                f.write(svg_content)
            print(f"Generated debug badge: '{badge_filename}' (Display: '{service_display_name_for_badge}', Color: {color})")
        except Exception as e:
            print(f"Error writing debug badge file {badge_filename}: {e}")
        
        print("Debug badge generation complete.")
        sys.exit(0)

    # --- If not --debug-badge, proceed with URL scraping ---
    print(f"Scraping status from: {args.status_url}")
    services_status = asyncio.run(run_scraper_with_timeout(args.status_url, args.executable_path, args.timeout))

    if not services_status:
        print("No service statuses found after scraping.")
        services_status = {'Scraping Status': 'No Data'}

    print(f"Found {len(services_status)} services (including potential error statuses).")

    print(f"Clearing existing badges in {output_dir}")
    for existing_file in os.listdir(output_dir):
        if existing_file.endswith('.svg'):
            try:
                os.remove(os.path.join(output_dir, existing_file))
            except OSError as e:
                 print(f"Error removing old badge {existing_file}: {e}")

    for service_key_original, status_value in services_status.items():
        # Clean the service name to remove any status information
        service_display_name_for_badge = clean_service_name(service_key_original, status_value)
        service_display_name_for_badge = service_display_name_for_badge.replace('_', ' ')
        
        filename_base = sanitize_service_name_for_filename(service_display_name_for_badge)
        badge_filename = os.path.join(output_dir, f"{filename_base}.svg")
        color = get_status_color(status_value)
        svg_content = create_badge_svg(service_display_name_for_badge, status_value, color)

        try:
            with open(badge_filename, "w", encoding="utf-8") as f:
                f.write(svg_content)
            print(f"Original Key: '{service_key_original}', Status: '{status_value}' -> Display: '{service_display_name_for_badge}', File: '{badge_filename}', Color: {color}")
        except Exception as e:
            print(f"Error writing badge file {badge_filename}: {e}")

    if 'Scraping Status' in services_status and services_status['Scraping Status'] != 'No Data':
        print("Scraping process encountered an error.")
    print("Badge generation complete.")
