# An example of a pythonrc file that can be used within a REPL session.
from pythonrc import *
from fetcher import revolut as rev
(pw, browser, context, p) = ruc(start_playwright())
ruc(rev.login(p))
ruc(rev.accept_cookies_on_revolut(p))
ruc(p.get_by_role("tab", name="Excel").click())
ruc(p.locator("//div[normalize-space(text()) = 'Starting on']/..").click())
