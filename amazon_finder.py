"""
AMAZON FINDER - Product Search for BOOMER
Finds ANY Amazon product and returns affiliate link

Uses multiple methods:
1. Direct ASIN lookup (if ASIN provided)
2. Amazon search via DuckDuckGo (no API key needed)
3. GPT to extract product info from search results
"""

import os
import re
import json
import requests
from urllib.parse import quote_plus, urlencode
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

AFFILIATE_TAG = "paulstxmbur-20"


class AmazonFinder:
    """
    Finds Amazon products for BOOMER to sell
    No API keys required - uses web search
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def search_product(self, query, max_results=3):
        """
        Search for a product and return Amazon results with affiliate links

        Args:
            query: Product search query (e.g., "Jarrow Formulas MK-7")
            max_results: Maximum number of results to return

        Returns:
            List of products with name, price estimate, amazon_link, asin
        """

        print(f"[AmazonFinder] Searching for: {query}")

        # Method 1: Try DuckDuckGo search for Amazon products
        products = self._search_via_duckduckgo(query, max_results)

        if products:
            return products

        # Fallback: Use GPT to generate likely ASIN based on product knowledge
        return self._gpt_product_lookup(query)

    def _search_via_duckduckgo(self, query, max_results=3):
        """Search DuckDuckGo for Amazon products"""

        try:
            # Search specifically for Amazon results
            search_query = f"site:amazon.com {query}"
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}"

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                print(f"[AmazonFinder] DuckDuckGo search failed: {response.status_code}")
                return []

            # Extract Amazon URLs and titles from results
            products = []

            # Find Amazon product links
            # Pattern matches: amazon.com/dp/ASIN or amazon.com/gp/product/ASIN
            asin_pattern = r'amazon\.com(?:/[^/]+)?/(?:dp|gp/product)/([A-Z0-9]{10})'

            matches = re.findall(asin_pattern, response.text)
            unique_asins = list(dict.fromkeys(matches))[:max_results]

            for asin in unique_asins:
                product = self._create_product_from_asin(asin, query)
                if product:
                    products.append(product)

            return products

        except Exception as e:
            print(f"[AmazonFinder] DuckDuckGo search error: {e}")
            return []

    def _create_product_from_asin(self, asin, original_query):
        """Create a product dict from an ASIN"""

        affiliate_link = f"https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}"

        # Use GPT to generate product name and estimate price
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a product information assistant. Given a search query for an Amazon product, provide the likely product name and estimated price. Return JSON with 'name' and 'price' fields."},
                    {"role": "user", "content": f"Search query: {original_query}\nAmazon ASIN: {asin}\n\nProvide the likely product name and estimated USD price."}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            info = json.loads(response.choices[0].message.content)

            return {
                "name": info.get("name", original_query),
                "price": float(info.get("price", 30)),
                "rating": 4.5,  # Assume good rating
                "amazon": asin,
                "amazon_link": affiliate_link,
                "category": "Amazon Find",
                "source": "amazon_search"
            }

        except Exception as e:
            print(f"[AmazonFinder] GPT product info error: {e}")
            return {
                "name": original_query,
                "price": 30,
                "rating": 4.0,
                "amazon": asin,
                "amazon_link": affiliate_link,
                "category": "Amazon Find",
                "source": "amazon_search"
            }

    def _gpt_product_lookup(self, query):
        """Use GPT to find likely Amazon products and ASINs"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """You are an Amazon product expert. Given a product search query, provide 1-3 real Amazon products that match.

For each product, provide:
- name: Full product name as it appears on Amazon
- price: Approximate USD price
- asin: The 10-character Amazon ASIN if you know it (or your best guess based on common products)
- category: Product category

Return as JSON array. Be as accurate as possible with ASINs for popular health/supplement products."""},
                    {"role": "user", "content": f"Find Amazon products matching: {query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )

            result = json.loads(response.choices[0].message.content)
            products_data = result.get("products", result.get("results", []))

            if isinstance(products_data, list):
                products = []
                for p in products_data[:3]:
                    asin = p.get("asin", "")
                    if asin and len(asin) == 10:
                        products.append({
                            "name": p.get("name", query),
                            "price": float(p.get("price", 30)),
                            "rating": 4.5,
                            "amazon": asin,
                            "amazon_link": f"https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}",
                            "category": p.get("category", "Amazon Find"),
                            "source": "gpt_lookup"
                        })
                return products

        except Exception as e:
            print(f"[AmazonFinder] GPT lookup error: {e}")

        return []

    def get_affiliate_link(self, asin_or_url):
        """
        Convert an ASIN or Amazon URL to an affiliate link

        Args:
            asin_or_url: Either a 10-char ASIN or an Amazon URL

        Returns:
            Affiliate link string
        """

        # Check if it's already a full URL
        if "amazon.com" in asin_or_url:
            # Extract ASIN from URL
            asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', asin_or_url)
            if asin_match:
                asin = asin_match.group(1)
            else:
                # Try to use the URL as-is with tag added
                if "tag=" in asin_or_url:
                    return asin_or_url.replace(re.search(r'tag=[^&]+', asin_or_url).group(), f"tag={AFFILIATE_TAG}")
                elif "?" in asin_or_url:
                    return f"{asin_or_url}&tag={AFFILIATE_TAG}"
                else:
                    return f"{asin_or_url}?tag={AFFILIATE_TAG}"
        else:
            asin = asin_or_url

        return f"https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}"


# Singleton instance
amazon_finder = AmazonFinder()


def find_amazon_product(query, max_results=3):
    """Main entry point - find products on Amazon"""
    return amazon_finder.search_product(query, max_results)


def get_affiliate_link(asin_or_url):
    """Convert ASIN/URL to affiliate link"""
    return amazon_finder.get_affiliate_link(asin_or_url)


if __name__ == "__main__":
    # Test the finder
    print("=" * 60)
    print("AMAZON FINDER TEST")
    print("=" * 60)

    test_queries = [
        "Jarrow Formulas MK-7",
        "Life Extension Super K",
        "NOW Foods Vitamin D3 5000 IU"
    ]

    for query in test_queries:
        print(f"\nSearching: {query}")
        print("-" * 40)
        results = find_amazon_product(query)
        for product in results:
            print(f"  {product['name']}")
            print(f"    Price: ${product['price']}")
            print(f"    Link: {product['amazon_link']}")
        print()
