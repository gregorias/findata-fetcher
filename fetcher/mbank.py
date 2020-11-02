"""Fetches account data from mBank."""
import logging
import os
import re
from typing import List, NamedTuple

from cefpython3 import cefpython as cef  # type: ignore

__all__ = ['Credentials', 'fetch_raw_mbank_data']


class Credentials(NamedTuple):
    id: str
    pwd: str


MBANK_SPA_JS = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'mbankspa.js')
MBANK_LOGIN_PAGE = 'https://online.mbank.pl/pl/Login'
TFA_PAGE_PTRN = r'^https://online.mbank.pl/authorization(#/.*)?'
DESKTOP_PAGE = 'https://online.mbank.pl/pl#Desktop'
HISTORY_PAGE = 'https://online.mbank.pl/history'

# Here's where the CEF script will save scraped data.
mbank_data = None


class MbankLoginState:
    def __init__(self, cfg):
        self.cfg = cfg

    def visit(self, browser, frame):
        if frame.GetUrl() != MBANK_LOGIN_PAGE:
            logging.error('Expected page {0} but got {1}'.format(
                MBANK_LOGIN_PAGE, frame.GetUrl()))
            return None

        frame.ExecuteJavascript("""
            try {{
                document.getElementById("userID").value = "{username}";
                document.getElementById("pass").value = "{password}";
                // Simulate a key press to enable the submit button
                $('#pass').focus().trigger({{type : 'keydown', which : 65}});
                $('#pass').focus().trigger({{type : 'keypress', which : 65}});
                $('#pass').focus().trigger({{type : 'keyup', which : 65}});
                document.getElementById("submitButton").click();
            }} catch (e) {{
                closeBrowser('Could not login. ' + e.message);
            }}""".format(username=self.cfg.id, password=self.cfg.pwd))
        return MbankDesktopState()


class MbankDesktopState:
    def visit(self, browser, frame):
        logging.debug('MbankDesktopState is visiting {0}'.format(
            frame.GetUrl()))
        ASPX_PAGE = 'https://online.mbank.pl/csite/top.aspx'
        if frame.GetUrl() == ASPX_PAGE:
            # This should be an auto-redirect page.
            return self
        elif re.match(TFA_PAGE_PTRN, frame.GetUrl()):
            # This should be a second factor authentication page
            return self
        elif frame.GetUrl() == DESKTOP_PAGE:
            # Desktop page is the start page but we want to go to transaction
            # history page.
            browser.Navigate(HISTORY_PAGE)
            return self
        elif frame.GetUrl() == HISTORY_PAGE:
            load_new_javascript(browser)
            return self
        else:
            return self


class LoadHandler:
    """A state machine-crawler that traverses the site."""
    def __init__(self, state):
        self.state = state

    def OnLoadEnd(self, browser, frame, http_code):
        logging.debug('LoadHandler({0})'.format(frame.GetUrl()))
        try:
            # For some reason going to the logout page gives http_code 0
            if http_code // 100 not in [0, 2]:
                logging.error(
                    ('Could not load a new page successfully: {0} {1}').format(
                        browser.GetUrl(), http_code))
                browser.TryCloseBrowser()
                return

            next_state = self.state.visit(browser, frame)
            if not next_state:
                logging.debug('LoadHandler has reached an end state.')
                browser.TryCloseBrowser()
                return
            self.state = next_state
        except Exception as e:
            logging.error('Caught {0} in LoadHandler.OnLoadEnd'.format(e))
            browser.TryCloseBrowser()


# Browser bindings. They get assigned to a window object, so they do not
# disappear on page changes.
def js_log(msg):
    logging.debug('JS.jsLog: {0}'.format(msg))


def set_result(result):
    global mbank_data
    mbank_data = result
    return True


def load_new_javascript(browser):
    with open(MBANK_SPA_JS, 'r') as js:
        browser.GetFocusedFrame().ExecuteJavascript(js.read())


def fetch_mbank_data_internal(creds: Credentials) -> List[List[str]]:
    """Runs a CEF browser to fetch data from mBank.

    Returns:
        An array of arrays. Each atomic array consists of 4 strings:
        [date, title, tr amount, end saldo].
    """
    BROWSER_RECT = [100, 100, 100 + 1024, 100 + 768]

    wi = cef.WindowInfo()
    wi.SetAsChild(0, windowRect=BROWSER_RECT)
    browser = cef.CreateBrowserSync(window_info=wi,
                                    url=MBANK_LOGIN_PAGE,
                                    window_title='Browser')
    lh = LoadHandler(MbankLoginState(creds))
    browser.SetClientHandler(lh)
    jb = cef.JavascriptBindings()

    jb.SetFunction('setResult', set_result)
    jb.SetFunction('jsLog', js_log)
    jb.SetFunction('loadNew', lambda: load_new_javascript(browser))
    browser.SetJavascriptBindings(jb)

    logging.debug('Starting the CEF message loop.')
    cef.MessageLoop()

    if not mbank_data:
        raise Exception('The javascript has not returned a result.')
    if isinstance(mbank_data, str):
        logging.error('Could not scrape the data. {0}'.format(mbank_data))
        raise Exception(mbank_data)
    return mbank_data


def fetch_raw_mbank_data(creds: Credentials) -> List[List[str]]:
    """Runs CEF to fetch raw data from mBank.

    Returns:
        A list of transaction record. Each record consists of 4 strings:

        * date,
        * title,
        * transaction amount,
        * end saldo.

        The list is provided in the order they appear on the Mbank page.
    """
    cef.Initialize()
    try:
        return fetch_mbank_data_internal(creds)
    finally:
        logging.debug('Shutting down CEF.')
        cef.Shutdown()
