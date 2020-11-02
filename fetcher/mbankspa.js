// Copyright (C) 2019 Grzegorz Milka
// This file implements the mBank SPA crawler that crawls mBank's site and
// gleans my account information.
//
// The script is meant to be used with the fetchmbank.py module which sets up
// the necessary environment for communication. At the end of the script
// setResult is called with a array representing mBank's data or a string
// beginning with 'Error: '.

DESKTOP_PAGE = 'https://online.mbank.pl/pl#/Desktop'

function sleep(ms) {
  return new Promise((done) => setTimeout(done, ms));
}

/**
 * Runs cb until it is true or it has been run count number of times.
 *
 * Returns the output of cb().
 */
async function probeTillTrue(cb) {
  TRIES = 10;
  TIMEOUT = 1000;
  for (var i = 0; i < TRIES; ++i) {
    if (cb()) break;
    await sleep(TIMEOUT);
  }
  return cb();
}

/**
 * Finds the "Saldo" text span.
 */
function findSaldo() {
  var xpath = "//span[contains(text(),'Saldo')]";
  return document.evaluate(xpath, document, null,
    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}

/**
 * Returns whether the history page shows end saldos.
 */
function isSaldoOn() {
  // Using the saldo text span, navigate to the ball to see its color.
  saldoSpan = findSaldo()
  saldoBall = saldoSpan.parentNode.children[2].children[1]
  bc = saldoBall.computedStyleMap().get("background-color")
  // A white ball means that end saldos are not visible.
  return bc != 'rgb(255, 255, 255)'
}

/**
 * Instructs the SPA to show end saldos.
 */
async function showSaldo() {
  saldo_span = await probeTillTrue(findSaldo);
  if (!saldo_span) throw new Error('Could not find the saldo button.');
  if (isSaldoOn()) return;
  saldo_span.click();
}
function findTransactionTable() {
  var xpath = "//tbody";
  return document.evaluate(xpath, document, null,
    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}

function scrapeTransaction(tr) {
  if (!tr.tagName == 'TR')
    throw new Error('Expected a TR node.');

  cs = tr.children;
  return [
    cs[1].innerText, // 28.10.2019
    cs[3].innerText, // TITLE OF THE TRANSACTION
    cs[6].innerText, // -15,00 PLN
    cs[7].innerText  // 1 949,00 PLN
  ];
}

async function scrapeLatestTransactions() {
  theTable = await probeTillTrue(findTransactionTable);
  if (!theTable) throw new Error('Could not find the transaction table.');
  trs = [];
  for (idx = 0; idx < theTable.children.length; idx += 2) {
    trs.push(scrapeTransaction(theTable.children[idx]));
  }
  jsLog(trs);
  return trs
}

async function main() {
  try {
    jsLog('main()');
    if (window.location != 'https://online.mbank.pl/history')
      throw new Error('showSaldo wasn\'t called on the history page.');
    showSaldo();
    transactions = await scrapeLatestTransactions();
    jsLog(transactions)
    setResult(transactions);
  } catch (e) {
    setResult('Error: ' + e.message);
  } finally {
    window.location = "/LoginMain/Account/Logout"
  }
}

// Executing main inside a timeout, because javascript bindings set from Python
// are not visible if we just execute main() in this thread. An alternative
// solution is to run alert() before main().
//
// Also wait some time for the site to load fully. Alternatively I could check
// for an element that would indicate full load but I haven't spent time finding
// out a good indicator.
setTimeout(main, 5000);
