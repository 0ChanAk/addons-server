$(document).ready(function(){

var catFixture = {
    setup: function() {
        this.sandbox = tests.createSandbox('#addon-cats');
        initCatFields();
    },
    teardown: function() {
        this.sandbox.remove();
    }
};

module('initCatFields', catFixture);

test('Default with initial categories', function() {
    var scope = $("#addon-cats-fx", self.sandbox);
    var checkedChoices = $("input:checked", scope);
    equals(checkedChoices.length, 2);
    equals(checkedChoices[0].id, "id_form-0-categories_1");
    equals(checkedChoices[1].id, "id_form-0-categories_2");

    // 2 categories are selected, the other category should be disabled.
    var max = scope.parent("div").attr("data-max-categories");
    equals(parseInt(max), 2);
    var disabledChoices = $("input:disabled", scope);
    equals(disabledChoices.length, 1);
    equals(disabledChoices[0].id, "id_form-0-categories_0");
});

test('Default without initial categories', function() {
    equals($("#addon-cats-tb input:checked", self.sandbox).length, 0);
});


function pushTiersAndResults($suite, tiers, results) {
    $.each(['1','2','3','4'], function(i, val) {
        tiers.push($('[class~="test-tier"][data-tier="' + val + '"]',
                                                                $suite));
        results.push($('[class~="tier-results"][data-tier="' + val + '"]',
                                                                $suite));
    });
}

var validatorFixtures = {
    setup: function() {
        this.sandbox = tests.createSandbox('#addon-validator-template');
        $.mockjaxSettings = {
            status: 200,
            responseTime: 0,
            contentType: 'text/json',
            dataType: 'json'
        };
    },
    teardown: function() {
        $.mockjaxClear();
        this.sandbox.remove();
    }
};


module('Validator: Passing Validation', validatorFixtures);

asyncTest('Test passing', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        response: function(settings) {
            this.responseText = {
                "validation": {
                    "errors": 0,
                    "detected_type": "extension",
                    "success": true,
                    "warnings": 1,
                    "notices": 0,
                    "message_tree": {},
                    "messages": [],
                    "rejected": false,
                    "metadata": {
                        "version": "1.3a.20100704",
                        "id": "developer@somewhere.org",
                        "name": "The Add One"
                    }
                }
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-passed');
    }).thenDo(function() {
        pushTiersAndResults($suite, tiers, results);
        $.each(tiers, function(i, tier) {
            var tierN = i+1;
            ok(tier.hasClass('tests-passed'),
                'Checking class: ' + tier.attr('class'));
            equals(tier.hasClass('ajax-loading'), false,
                'Checking class: ' + tier.attr('class'));
            equals($('.tier-summary', tier).text(),
                   '0 errors, 0 warnings');
            // Note: still not sure why there is a period at the end
            // here (even though it's getting cleared)
            equals($('#suite-results-tier-' + tierN.toString() +
                     ' .result-summary').text(),
                   '0 errors, 0 warnings.');
        });
        $.each(results, function(i, result) {
            ok(result.hasClass('tests-passed'),
                'Checking class: ' + result.attr('class'));
            equals(result.hasClass('ajax-loading'), false,
                'Checking class: ' + result.attr('class'));
        });
        equals($('.suite-summary span', $suite).text(),
               'Add-on passed validation.');
        start();
    });
});


module('Validator: Failing Validation', validatorFixtures);

asyncTest('Test failing', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        response: function(settings) {
            this.responseText = {
                "validation": {
                    "errors": 1,
                    "detected_type": "extension",
                    "success": false,
                    "warnings": 1,
                    "notices": 0,
                    "message_tree": {
                        "testcases_targetapplication": {
                            "__messages": [],
                            "__warnings": 1,
                            "__errors": 1,
                            "__notices": 0,
                            "test_targetedapplications": {
                                "invalid_max_version": {
                                    "__messages": ["96dc9924ec4c11df991a001cc4d80ee4"],
                                    "__warnings": 0,
                                    "__errors": 1,
                                    "__notices": 0
                                },
                                "__notices": 0,
                                "missing_seamonkey_installjs": {
                                    "__messages": ["96dca428ec4c11df991a001cc4d80ee4"],
                                    "__warnings": 1,
                                    "__errors": 0,
                                    "__notices": 0
                                },
                                "__warnings": 1,
                                "__errors": 1,
                                "__messages": []
                            }
                        }
                    },
                    "messages": [
                        {
                            "context": null,
                            "description": ["The maximum version that was specified is not an acceptable version number for the Mozilla product that it corresponds with.", "Version \"4.0b2pre\" isn't compatible with {ec8030f7-c20a-464f-9b0e-13a3a9e97384}."],
                            "column": 0,
                            "id": ["testcases_targetapplication", "test_targetedapplications", "invalid_max_version"],
                            "file": "install.rdf",
                            "tier": 1,
                            "message": "Invalid maximum version number",
                            "type": "error",
                            "line": 0,
                            "uid": "afdc9924ec4c11df991a001cc4d80ee4"
                        },
                        {
                            "context": null,
                            "description": "SeaMonkey requires install.js, which was not found. install.rdf indicates that the addon supports SeaMonkey.",
                            "column": 0,
                            "id": ["testcases_targetapplication", "test_targetedapplications", "missing_seamonkey_installjs"],
                            "file": "install.rdf",
                            "tier": 2,
                            "message": "Missing install.js for SeaMonkey.",
                            "type": "warning",
                            "line": 0,
                            "uid": "96dca428ec4c11df991a001cc4d80ee4"
                        }
                    ],
                    "rejected": false,
                    "metadata": {
                        "version": "1.3a.20100704",
                        "id": "developer@somewhere.org",
                        "name": "The Add One"
                    }
                }
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        var missingInstall, invalidVer;
        pushTiersAndResults($suite, tiers, results);
        $.each(tiers, function(i, tier) {
            var tierN = i+1;
            equals(tier.hasClass('ajax-loading'), false,
                'Checking class: ' + tier.attr('class'));
            switch (tierN) {
                case 1:
                    ok(tier.hasClass('tests-failed'),
                       'Checking class: ' + tier.attr('class'));
                    break;
                default:
                    ok(tier.hasClass('tests-passed'),
                       'Checking class: ' + tier.attr('class'));
                    break;
            }
        });
        $.each(results, function(i, result) {
            var tierN = i+1;
            equals(result.hasClass('ajax-loading'), false,
                   'Checking class: ' + result.attr('class'));
            switch (tierN) {
                case 1:
                    ok(result.hasClass('tests-failed'),
                       'Checking class: ' + result.attr('class'));
                    break;
                case 2:
                    ok(result.hasClass('tests-passed-warnings'),
                       'Checking class: ' + result.attr('class'));
                    break;
                default:
                    ok(result.hasClass('tests-passed'),
                       'Checking class: ' + result.attr('class'));
                    break;
            }
        });
        equals($('#suite-results-tier-1 .result-summary', $suite).text(),
               '1 error, 0 warnings');
        equals($('#suite-results-tier-2 .result-summary', $suite).text(),
               '0 errors, 1 warning');
        missingInstall = $('#v-msg-96dca428ec4c11df991a001cc4d80ee4', $suite);
        equals(missingInstall.length, 1);
        equals(missingInstall.parent().attr('data-tier'), "2",
               "not attached to tier 2");
        equals(missingInstall.attr('class'), 'msg msg-warning');
        equals($('h5', missingInstall).text(),
               'Missing install.js for SeaMonkey.');
        equals($('p', missingInstall).text(),
               'Warning: SeaMonkey requires install.js, which was not ' +
               'found. install.rdf indicates that the addon supports ' +
               'SeaMonkey.');
        installVer = $('#v-msg-afdc9924ec4c11df991a001cc4d80ee4', $suite);
        equals(installVer.length, 1);
        equals(installVer.parent().attr('data-tier'), "1",
               "not attached to tier 1");
        equals(installVer.attr('class'), 'msg msg-error');
        equals($('p', installVer).text(),
               'Error: The maximum version that was specified is not an ' +
               'acceptable version number for the Mozilla product that ' +
               'it corresponds with.Error: Version \"4.0b2pre\" isn\'t ' +
               'compatible with {ec8030f7-c20a-464f-9b0e-13a3a9e97384}.');
        equals($('.suite-summary span', $suite).text(),
               'Add-on failed validation.');
        equals($('#suite-results-tier-4 .tier-results span').text(),
               'All tests passed successfully.');
        start();
    });
});


var compatibilityFixtures = {
    setup: function() {
        this.sandbox = tests.createSandbox('#addon-compatibility-template');
        $.mockjaxSettings = {
            status: 200,
            responseTime: 0,
            contentType: 'text/json',
            dataType: 'json'
        };
    },
    teardown: function() {
        $.mockjaxClear();
        this.sandbox.remove();
    }
};

module('Validator: Compatibility', compatibilityFixtures);

asyncTest('Test passing', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": null,
            "validation": {
                "errors": 0,
                "success": false,
                "warnings": 5,
                "ending_tier": 5,
                "messages": [{
                    "context": null,
                    "description": ["Some non-compatibility warning."],
                    "column": null,
                    "id": ["testcases_packagelayout", "test_blacklisted_files", "disallowed_extension"],
                    "file": "ffmpeg/libmp3lame-0.dll",
                    "tier": 1,
                    "for_appversions": null,
                    "message": "Flagged file extension found",
                    "type": "warning",
                    "line": null,
                    "uid": "bb0b38812d8f450a85fa90a2e7e6693b"
                },
                {
                    "context": ["<code>"],
                    "description": ["A dangerous or banned global..."],
                    "column": 23,
                    "id": [],
                    "file": "chrome/content/youtune.js",
                    "tier": 3,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.0b3"]
                    },
                    "message": "Dangerous Global Object",
                    "type": "warning",
                    "line": 533,
                    "uid": "2a96f7faee7a41cca4d6ead26dddc6b3"
                },
                {
                    "context": ["<code>"],
                    "description": ["some other error..."],
                    "column": 23,
                    "id": [],
                    "file": "file.js",
                    "tier": 3,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.0b3"]
                    },
                    "message": "Some error",
                    "type": "error",
                    "line": 533,
                    "uid": "dd96f7faee7a41cca4d6ead26dddc6c2"
                },
                {
                    "context": ["<code>"],
                    "description": "To prevent vulnerabilities...",
                    "column": 2,
                    "id": [],
                    "file": "chrome/content/youtune.js",
                    "tier": 3,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.0b1"]
                    },
                    "message": "on* attribute being set using setAttribute",
                    "type": "notice",
                    "line": 226,
                    "uid": "9a07163bb74e476c96a2bd467a2bbe52"
                },
                {
                    "context": null,
                    "description": "The add-on doesn\'t have...",
                    "column": null,
                    "id": [],
                    "file": "chrome.manifest",
                    "tier": 4,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.0b1"]
                    },
                    "message": "Add-on cannot be localized",
                    "type": "notice",
                    "line": null,
                    "uid": "92a0be84024a464e87046b04e26232c4"
                }],
                "detected_type": "extension",
                "notices": 2,
                "message_tree": {},
                "metadata": {}
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        // Wait until last app/version section was created.
        return $('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b1', $suite).length;
    }).thenDo(function() {
        equals($('#suite-results-tier-errors', $suite).length, 0);
        equals($('.result-header h4:visible', $suite).eq(0).text(),
               'General Tests');
        equals($('.result-header h4:visible', $suite).eq(1).text(),
               'Firefox 4.0b3 Tests');
        equals($('.result-header h4:visible', $suite).eq(2).text(),
               'Firefox 4.0b1 Tests');
        equals($('#v-msg-2a96f7faee7a41cca4d6ead26dddc6b3 p:eq(0)', $suite).text(),
               'Warning: A dangerous or banned global...');
        equals($('#v-msg-9a07163bb74e476c96a2bd467a2bbe52 p:eq(0)', $suite).text(),
               'Error: To prevent vulnerabilities...');
        equals($('#v-msg-92a0be84024a464e87046b04e26232c4 p:eq(0)', $suite).text(),
               'Error: The add-on doesn\'t have...');
        ok($('#v-msg-bb0b38812d8f450a85fa90a2e7e6693b', $suite).length == 1,
           'Non-compatibility message should be shown');
        equals($('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b3 .result-summary', $suite).text(),
               '1 error, 1 warning');
        equals($('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b3 .version-change-link').attr('href'),
               '/firefox-4-changes');
        equals($('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b1 .version-change-link').length, 0);
        equals($('#suite-results-tier-1 .result-summary', $suite).text(),
               '0 errors, 1 warning');
        start();
    });
});

asyncTest('Test task error', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": "Traceback (most recent call last):\n  File \"/Users/kumar/dev/zamboni/apps/devhub/tasks.py\", line 23, in validator\n    result = _validator(upload)\n  File \"/Users/kumar/dev/zamboni/apps/devhub/tasks.py\", line 49, in _validator\n    import validator.main as addon_validator\n  File \"/Users/kumar/dev/zamboni/vendor/src/amo-validator/validator/main.py\", line 17, in <module>\n    import validator.testcases.l10ncompleteness\n  File \"/Users/kumar/dev/zamboni/vendor/src/amo-validator/validator/testcases/l10ncompleteness.py\", line 3, in <module>\n    import chardet\nImportError: No module named chardet\n",
            "validation": ""
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('#suite-results-tier-1 .msg', $suite).length > 0;
    }).thenDo(function() {
        equals($('.msg', $suite).text(),
               'ErrorError: Validation task could not complete or ' +
               'completed with errors');
        equals($('.msg:visible', $suite).length, 1);
        start();
    });
});

asyncTest('Test no tests section', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": null,
            "validation": {
                "errors": 0,
                "success": false,
                "warnings": 1,
                "ending_tier": 5,
                "messages": [{
                    "context": ["<code>"],
                    "description": ["A dangerous or banned global..."],
                    "column": 23,
                    "id": [],
                    "file": "chrome/content/youtune.js",
                    "tier": 3,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.0b3"]
                    },
                    "message": "Dangerous Global Object",
                    "type": "warning",
                    "line": 533,
                    "uid": "2a96f7faee7a41cca4d6ead26dddc6b3"
                }],
                "detected_type": "extension",
                "notices": 2,
                "message_tree": {},
                "metadata": {}
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        // Wait until last app/version section was created.
        return $('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b3', $suite).length;
    }).thenDo(function() {
        equals($('#suite-results-tier-non_compat:visible', $suite).length, 0);
        equals($('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b3 .msg', $suite).length, 1);
        start();
    });
});

asyncTest('Test compat error override', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": null,
            "validation": {
                "errors": 0,
                "compatibility_summary": {"errors": 1},
                "success": false,
                "warnings": 1,
                "ending_tier": 5,
                "messages": [{
                    "context": ["<code>"],
                    "description": ["A dangerous or banned global..."],
                    "column": 23,
                    "id": [],
                    "file": "chrome/content/youtune.js",
                    "tier": 3,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.0b3"]
                    },
                    "message": "Dangerous Global Object",
                    "type": "warning",
                    "compatibility_type": "error",
                    "line": 533,
                    "uid": "2a96f7faee7a41cca4d6ead26dddc6b3"
                }],
                "detected_type": "extension",
                "notices": 0,
                "message_tree": {},
                "metadata": {}
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        // Wait until last app/version section was created.
        return $('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b3', $suite).length;
    }).thenDo(function() {
        var $msg = $('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-40b3 .msg', $suite);
        ok($msg.hasClass('msg-error'),
           'Expected msg-error, got: ' + $msg.attr('class'));
        start();
    });
});

asyncTest('Test basic error override', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": null,
            "validation": {
                "errors": 0,
                "compatibility_summary": {"errors": 1},
                "success": false,
                "warnings": 1,
                "ending_tier": 5,
                "messages": [{
                    "context": ["<code>"],
                    "description": ["Contains binary components..."],
                    "column": 23,
                    "id": [],
                    "file": "chrome/content/youtune.dll",
                    "tier": 1,
                    "for_appversions": null,
                    "message": "Contains Binary Components",
                    "type": "warning",
                    "compatibility_type": "error",
                    "line": 533,
                    "uid": "2a96f7faee7a41cca4d6ead26dddc6b3"
                }],
                "detected_type": "extension",
                "notices": 0,
                "message_tree": {},
                "metadata": {}
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('#suite-results-tier-1 .msg', $suite).length;
    }).thenDo(function() {
        var $msg = $('#suite-results-tier-1 .msg', $suite);
        ok($msg.hasClass('msg-error'),
           'Expected msg-error, got: ' + $msg.attr('class'));
        start();
    });
});

asyncTest('Test single tier', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": null,
            "validation": {
                "errors": 0,
                "success": false,
                "warnings": 5,
                "compatibility_summary": {
                    "notices": 1,
                    "errors": 2,
                    "warnings": 0
                },
                "ending_tier": 5,
                "messages": [{
                    "context": null,
                    "compatibility_type": "notice",
                    "uid": "bc73cbff60534798b46ed5840d1544c6",
                    "column": null,
                    "line": null,
                    "file": "",
                    "tier": 5,
                    "for_appversions": {
                        "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}": ["4.2a1pre", "5.0a2", "6.0a1", "4.0.*"]
                    },
                    "message": "Firefox 5 Compatibility Detected",
                    "type": "notice",
                    "id": ["testcases_compatibility", "firefox_5_test", "fx5_notice"],
                    "description": "Potential compatibility for FX5 was detected."
                }],
                "detected_type": "extension",
                "notices": 2,
                "message_tree": {},
                "metadata": {}
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        // Wait until last app/version section was created.
        return $('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-42a1pre', $suite).length;
    }).thenDo(function() {
        // This was failing with tier not found
        equals($('#suite-results-tier-ec8030f7-c20a-464f-9b0e-13a3a9e97384-42a1pre .msg', $suite).length, 1);
        start();
    });
});

asyncTest('Test no compat tests', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        responseText: {
            "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
            "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
            "error": null,
            "validation": {
                "errors": 1,
                "success": false,
                "warnings": 7,
                "compatibility_summary": {
                    "notices": 0,
                    "errors": 0,
                    "warnings": 0
                },
                "ending_tier": 5,
                "messages": [{
                    "context": null,
                    "description": ["Non-compat error."],
                    "column": null,
                    "compatibility_type": null,
                    "file": "components/cooliris.dll",
                    "tier": 1,
                    "for_appversions": null,
                    "message": "Some error",
                    "type": "error",
                    "line": null,
                    "uid": "6fd1f5c74c4445f79a1919c8480e4e72"
                }],
                "detected_type": "extension",
                "notices": 2,
                "message_tree": {},
                "metadata": {}
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('#suite-results-tier-1 .msg', $suite).length;
    }).thenDo(function() {
        // template is hidden
        equals($('.template .result:visible', $suite).length, 0);
        // The non-compat error exists
        equals($('#v-msg-6fd1f5c74c4445f79a1919c8480e4e72', $suite).length, 1);
        start();
    });
});


module('Validator: Incomplete', validatorFixtures);

asyncTest('Test incomplete validation', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        response: function(settings) {
            this.responseText = {
                "url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38/json",
                "full_report_url": "/upload/d5d993a5a2fa4b759ae2fa3b2eda2a38",
                "validation": {
                    "errors": 1,
                    "success": false,
                    "warnings": 0,
                    "ending_tier": 1,
                    "messages": [{
                        "context": null,
                        "description": "",
                        "column": 0,
                        "line": 0,
                        "file": "",
                        "tier": 1,
                        "message": "The XPI could not be opened.",
                        "type": "error",
                        "id": ["main", "test_package", "unopenable"],
                        "uid": "436fd18fb1b24ab6ae950ef18519c90d"
                    }],
                    "rejected": false,
                    "detected_type": "unknown",
                    "notices": 0,
                    "message_tree": {},
                    "metadata": {}
                },
                "upload": "d5d993a5a2fa4b759ae2fa3b2eda2a38",
                "error": null
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        var missingInstall, invalidVer;
        pushTiersAndResults($suite, tiers, results);
        $.each(tiers, function(i, tier) {
            var tierN = i+1;
            tests.lacksClass(tier, 'ajax-loading');
            switch (tierN) {
                case 1:
                    tests.hasClass(tier, 'tests-failed');
                    break;
                default:
                    tests.hasClass(tier, 'tests-notrun');
                    break;
            }
        });
        $.each(results, function(i, result) {
            var tierN = i+1;
            tests.lacksClass(result, 'ajax-loading');
            switch (tierN) {
                case 1:
                    tests.hasClass(result, 'tests-failed');
                    break;
                default:
                    tests.hasClass(result, 'tests-notrun');
                    break;
            }
        });
        equals($('#suite-results-tier-1 .result-summary', $suite).text(),
               '1 error, 0 warnings');
        equals($('#suite-results-tier-2 .result-summary', $suite).html(),
               '&nbsp;');
        start();
    });
});


module('Validator: 500 Error response', validatorFixtures);

asyncTest('Test 500 error', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        status: 500,
        responseText: '500 Internal Error'
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        pushTiersAndResults($suite, tiers, results);
        // First tier should have an internal server error,
        // the other tiers should not have run.
        $.each(tiers, function(i, tier) {
            tests.lacksClass(tier, 'ajax-loading');
            tests.lacksClass(tier, 'tests-passed');
            if (i == 0) {
                tests.hasClass(tier, 'tests-failed');
            } else {
                tests.hasClass(tier, 'tests-notrun');
            }
        });
        $.each(results, function(i, result) {
            tests.lacksClass(result, 'ajax-loading');
            tests.lacksClass(result, 'tests-passed');
            if (i == 0) {
                tests.hasClass(result, 'tests-failed');
            } else {
                tests.hasClass(result, 'tests-notrun');
            }
        });
        start();
    });
});


module('Validator: Timeout', validatorFixtures);

asyncTest('Test timeout', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        isTimeout: true
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        pushTiersAndResults($suite, tiers, results);
        // Firs tier should show the timeout error, other tiers did not run.
        $.each(tiers, function(i, tier) {
            tests.lacksClass(tier, 'ajax-loading');
            if (i == 0) {
                tests.hasClass(tier, 'tests-failed');
            } else {
                tests.hasClass(tier, 'tests-notrun');
            }
        });
        $.each(results, function(i, result) {
            tests.lacksClass(result, 'ajax-loading');
            if (i == 0) {
                tests.hasClass(result, 'tests-failed');
            } else {
                tests.hasClass(result, 'tests-notrun');
            }
        });
        start();
    });
});

module('Validator: task error', validatorFixtures);

asyncTest('Test task error', function() {
    var $suite = $('.addon-validator-suite', this.sandbox),
        tiers=[], results=[];

    $.mockjax({
        url: '/validate',
        status: 200,
        responseText: {
            "url": "validate",
            "validation": "",
            "upload": "fa8f7dc58a3542d1a34180b72d0f607f",
            "error": "Traceback (most recent call last):\n  File \"/Users/kumar/dev/zamboni/apps/devhub/tasks.py\", line 23, in validator\n    result = _validator(upload)\n  File \"/Users/kumar/dev/zamboni/apps/devhub/tasks.py\", line 49, in _validator\n    import validator.main as addon_validator\n  File \"/Users/kumar/dev/zamboni/vendor/src/amo-validator/validator/main.py\", line 17, in <module>\n    import validator.testcases.l10ncompleteness\n  File \"/Users/kumar/dev/zamboni/vendor/src/amo-validator/validator/testcases/l10ncompleteness.py\", line 3, in <module>\n    import chardet\nImportError: No module named chardet\n"}
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        pushTiersAndResults($suite, tiers, results);
        // First tier should show internal error, other tiers should not run.
        $.each(tiers, function(i, tier) {
            tests.lacksClass(tier, 'ajax-loading');
            if (i == 0) {
                tests.hasClass(tier, 'tests-failed');
            } else {
                tests.hasClass(tier, 'tests-notrun');
            }
        });
        $.each(results, function(i, result) {
            tests.lacksClass(result, 'ajax-loading');
            if (i == 0) {
                tests.hasClass(result, 'tests-failed');
            } else {
                tests.hasClass(result, 'tests-notrun');
            }
        });
        start();
    });
});

module('Validator: suport html', validatorFixtures);

asyncTest('Test html', function() {
    var $suite = $('.addon-validator-suite', this.sandbox), err;

    $.mockjax({
        url: '/validate',
        status: 200,
        response: function(settings) {
            this.responseText = {
                "validation": {
                    "errors": 1,
                    "success": false,
                    "warnings": 0,
                    "ending_tier": 3,
                    "messages": [{
                        "context": null,
                        "description": "The values supplied for &lt;em:id&gt; in the install.rdf file is not a valid UUID string.",
                        "column": 0,
                        "line": 0,
                        "file": "install.rdf",
                        "tier": 1,
                        "message": "The value of &lt;em:id&gt; is invalid.",
                        "type": "error",
                        "id": ["testcases_installrdf", "_test_id", "invalid"],
                        "uid": "3793e550026111e082c3c42c0301fe38"
                    }],
                    "rejected": false,
                    "detected_type": "extension",
                    "notices": 0,
                    "metadata": {
                        "version": "2",
                        "name": "OddNodd",
                        "id": "oddnoddd"
                    }
                }
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        err = $('#v-msg-3793e550026111e082c3c42c0301fe38', $suite);
        equals($('h5', err).text(),
               'The value of <em:id> is invalid.');
        equals($('p', err).text(),
               'Error: The values supplied for <em:id> in the install.rdf file is not a valid UUID string.');
        start();
    });
});

module('Validator: error summaries', validatorFixtures);

asyncTest('Test errors are brief', function() {
    var $suite = $('.addon-validator-suite', this.sandbox);

    $.mockjax({
        url: '/validate',
        status: 200,
        response: function(settings) {
            this.responseText = {
                "validation": {
                    "errors": 1,
                    "success": true,
                    "warnings": 0,
                    "ending_tier": 0,
                    "messages": [{
                        "context": null,
                        "description": "",
                        "column": 0,
                        "line": 0,
                        "file": "",
                        "tier": 1,
                        "message": "Unable to open XPI.",
                        "type": "error",
                        "id": ["main", "test_search"],
                        "uid": "dd5dab88026611e082c3c42c0301fe38"
                    }],
                    "rejected": false,
                    "detected_type": "search",
                    "notices": 0,
                    "message_tree": {},
                    "metadata": {}
                }
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-failed');
    }).thenDo(function() {
        equals($('[class~="msg-error"] h5', $suite).text(),
               'Unable to open XPI.');
        equals($('[class~="msg-error"] p', $suite).html(), '&nbsp;');
        start();
    });
});

module('Validator: code context', validatorFixtures);

asyncTest('Test code context', function() {
    var $suite = $('.addon-validator-suite', this.sandbox);

    $.mockjax({
        url: '/validate',
        status: 200,
        response: function(settings) {
            this.responseText = {
                "url": "/upload/",
                "full_report_url": "/upload/14bd1cb1ae0d4b11b86395b1a0da7058",
                "validation": {
                    "errors": 0,
                    "success": false,
                    "warnings": 1,
                    "ending_tier": 3,
                    "messages": [{
                        "context": ["&lt;baddddddd html garbage=#&#34;&#34;",
                                    "&lt;foozer&gt;", null],
                        "description": [
                            "There was an error parsing the markup document.",
                            "malformed start tag, at line 1, column 26"],
                        "column": 0,
                        "line": 1,
                        "file": "chrome/content/down.html",
                        "tier": 2,
                        "message": "Markup parsing error",
                        "type": "warning",
                        "id": ["testcases_markup_markuptester",
                               "_feed", "parse_error"],
                        "uid": "bb9948b604b111e09dfdc42c0301fe38"
                    }],
                    "rejected": false,
                    "detected_type": "extension",
                    "notices": 0
                },
                "upload": "14bd1cb1ae0d4b11b86395b1a0da7058",
                "error": null
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-passed');
    }).thenDo(function() {
        equals($('.context .file', $suite).text(),
               'chrome/content/down.html');
        equals($('.context .lines div:eq(0)', $suite).text(), '1');
        equals($('.context .lines div:eq(1)', $suite).text(), '2');
        equals($('.context .inner-code div:eq(0)', $suite).html(),
               '&lt;baddddddd html garbage=#""');
        equals($('.context .inner-code div:eq(1)', $suite).html(),
               '&lt;foozer&gt;');
        equals($('.context .inner-code div:eq(2)', $suite).html(),
               '');
        start();
    });
});


module('Validator: minimal code context', validatorFixtures);

asyncTest('Test code context', function() {
    var $suite = $('.addon-validator-suite', this.sandbox);

    $.mockjax({
        url: '/validate',
        status: 200,
        response: function(settings) {
            this.responseText = {
                "url": "/upload/",
                "full_report_url": "/upload/14bd1cb1ae0d4b11b86395b1a0da7058",
                "validation": {
                    "errors": 0,
                    "success": false,
                    "warnings": 1,
                    "ending_tier": 3,
                    "messages": [{
                        "context": null,
                        "description": ["Error in install.rdf"],
                        "column": 0,
                        "line": 1,
                        "file": ["silvermelxt_1.3.5.xpi",
                                 "chrome/silvermelxt.jar", "install.rdf",
                                 null],
                        "tier": 2,
                        "message": "Some error",
                        "type": "warning",
                        "id": [],
                        "uid": "bb9948b604b111e09dfdc42c0301fe38"
                    }],
                    "rejected": false,
                    "detected_type": "extension",
                    "notices": 0
                },
                "upload": "14bd1cb1ae0d4b11b86395b1a0da7058",
                "error": null
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-passed');
    }).thenDo(function() {
        equals($('.context .file', $suite).text(),
               'silvermelxt_1.3.5.xpi/chrome/silvermelxt.jar/install.rdf');
        start();
    });
});


module('Validator: code indentation', validatorFixtures);

asyncTest('Test code indentation', function() {
    var $suite = $('.addon-validator-suite', this.sandbox);

    $.mockjax({
        url: '/validate',
        status: 200,
        response: function(settings) {
            this.responseText = {
                "url": "/upload/",
                "full_report_url": "/upload/14bd1cb1ae0d4b11b86395b1a0da7058",
                "validation": {
                    "errors": 0,
                    "success": false,
                    "warnings": 1,
                    "ending_tier": 3,
                    "messages": [{
                        "context": [
                            "                    if(blah) {",
                            "                        setTimeout(blah);",
                            "                    }"],
                        "description": ["Dangerous global in somefile.js"],
                        "column": 0,
                        "line": 1,
                        "file": ["silvermelxt_1.3.5.xpi",
                                 "chrome/silvermelxt.jar", "somefile.js"],
                        "tier": 2,
                        "message": "Some error",
                        "type": "warning",
                        "id": [],
                        "uid": "bb9948b604b111e09dfdc42c0301fe38"
                    }, {
                        "context": ["foobar"],
                        "description": ["Something in somefile.js"],
                        "column": 0,
                        "line": 1,
                        "file": ["silvermelxt_1.3.5.xpi",
                                 "/path/to/somefile.js"],
                        "tier": 2,
                        "message": "Some error",
                        "type": "warning",
                        "id": [],
                        "uid": "dd5448b604b111e09dfdc42c0301fe38"
                    }],
                    "rejected": false,
                    "detected_type": "extension",
                    "notices": 0
                },
                "upload": "14bd1cb1ae0d4b11b86395b1a0da7058",
                "error": null
            };
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-passed');
    }).thenDo(function() {
        equals($('.context .file:eq(0)', $suite).text(),
               'silvermelxt_1.3.5.xpi/chrome/silvermelxt.jar/somefile.js');
        equals($('.context .inner-code div:eq(0)', $suite).html(),
               'if(blah) {');
        equals($('.context .inner-code div:eq(1)', $suite).html(),
               '&nbsp;&nbsp;&nbsp;&nbsp;setTimeout(blah);');
        equals($('.context .file:eq(1)', $suite).text(),
               'silvermelxt_1.3.5.xpi/path/to/somefile.js');
        start();
    });
});


module('validation counts', validatorFixtures);

asyncTest('error/warning count', function() {
    var $suite = $('.addon-validator-suite', this.sandbox);

    $.mockjax({
        url: '/validate',
        status: 200,
        response: function(settings) {
            this.responseText = {
                "error": null,
                "validation": {
                    "errors": 0,
                    "success": false,
                    "warnings": 1,
                    "ending_tier": 3,
                    "messages": [
                        {"tier": 1, "type": "warning", "uid": "a1"},
                        {"tier": 1, "type": "notice", "uid": "a2"},
                        {"tier": 1, "type": "notice", "uid": "a3"}
                    ],
                    "notices": 2
                }
            }
        }
    });

    $suite.trigger('validate');

    tests.waitFor(function() {
        return $('[class~="test-tier"][data-tier="1"]', $suite).hasClass(
                                                            'tests-passed');
    }).thenDo(function() {
        equals($('[class~="test-tier"][data-tier="1"] .tier-summary').text(),
               '0 errors, 3 warnings');
        equals($('#suite-results-tier-1 .result-summary').text(),
               '0 errors, 3 warnings.');
        start();
    });
});


module('addonUploaded', {
    setup: function() {
        this._FormData = z.FormData;
        z.FormData = tests.StubOb(z.FormData, {
            send: function() {}
        });
        this.sandbox = tests.createSandbox('#file-upload-template');
        $.fx.off = true;

        $('#upload-file-input', this.sandbox).addonUploader();

        this.el = $('#upload-file-input', this.sandbox)[0];
        this.el.files = [{
            size: 200,
            name: 'some-addon.xpi'
        }];

        $(this.el).trigger('change');
        // sets all animation durations to 0
        $.fx.off = true;
    },
    teardown: function() {
        $.fx.off = false;
        this.sandbox.remove();
        z.FormData = this._FormData;
        $.fx.off = false;
    }
});

test('JSON error', function() {
    $(this.el).trigger("upload_success_results",
                       [{name: 'somefile.txt'},
                        {'error': "Traceback (most recent call last): ...NameError"}]);

    ok($('#upload-status-bar', this.sandbox).hasClass('bar-fail'));
    equals($('#upload_errors', this.sandbox).text(),
           'Unexpected server error while validating.')
});

test('Too many messages', function() {
    var results = {
        validation: {
            "errors": 7,
            "success": false,
            "warnings": 0,
            "ending_tier": 3,
            "messages": [{
                "message": "Invalid maximum version number",
                "type": "error"
            },
            {
                "message": "Missing translation file",
                "type": "error"
            },
            {
                "message": "Missing translation file",
                "type": "error"
            },
            {
                "message": "Missing translation file",
                "type": "error"
            },
            {
                "message": "Missing translation file",
                "type": "error"
            },
            {
                "message": "Missing translation file",
                "type": "error"
            },
            {
                "message": "Missing translation file",
                "type": "error"
            }],
            "rejected": false,
            "detected_type": "extension",
            "notices": 0,
        },
        error: null,
        full_report_url: '/full-report'
    };

    $(this.el).trigger("upload_success_results",
                       [{name: 'somefile.txt'}, results]);

    equals($('#upload-status-results ul li', this.sandbox).length, 6);
    equals($('#upload-status-results ul li:eq(5)', this.sandbox).text(),
           '…and 2 more');
});


test('form errors are cleared', function() {
    var fxt = this;
    // Simulate django form errors from the POST
    this.sandbox.find('form').prepend(
        '<ul class="errorlist"><li>Duplicate UUID found.</li></ul>');

    $(this.el).trigger("upload_start", [{name: 'somefile.txt'}]);

    equals($('ul.errorlist', this.sandbox).length, 0);
});

test('Notices count as warnings', function() {

    var results = {
        validation: {
            "warnings": 4,
            "notices": 4,
            "errors": 0,
            "success": true,
            "ending_tier": 3,
            "rejected": false,
            "detected_type": "extension"
        },
        error: null,
        full_report_url: '/full-report',
        platforms_to_exclude: []
    };

    $(this.el).trigger("upload_success_results",
                       [{name: 'somefile.txt'}, results]);

    equals($('##upload-status-results strong', this.sandbox).text(),
           'Your add-on passed validation with no errors and 8 warnings.');
});

test('HTML in errors', function() {
    var results = {
        validation: {
            "errors": 1,
            "success": false,
            "warnings": 0,
            "ending_tier": 3,
            "messages": [{
                // TODO(Kumar) when validator is no longer escaped, change this
                "message": "invalid properties in the install.rdf like &lt;em:id&gt;",
                "type": "error"
            }],
            "rejected": false,
            "detected_type": "extension",
            "notices": 0,
        },
        error: null,
        full_report_url: '/full-report'
    };
    $(this.el).trigger("upload_success_results",
                       [{name: 'somefile.txt'}, results]);
    ok($('#upload-status-bar', this.sandbox).hasClass('bar-fail'));
    equals($('#upload_errors', this.sandbox).text(),
           'invalid properties in the install.rdf like <em:id>')
});

test('HTML in filename (on start)', function() {
    $(this.el).trigger("upload_start", [{name: "tester's add-on2.xpi"}]);
    equals($('#upload-status-text', this.sandbox).text(),
           "Uploading tester's add-on2.xpi");
});

test('HTML in filename (on error)', function() {
    var errors = [],
        results = {};
    $(this.el).trigger("upload_errors",
                       [{name: "tester's add-on2.xpi"}, errors, results]);
    equals($('#upload-status-text', this.sandbox).text(),
           "Error with tester's add-on2.xpi");
});

test('HTML in filename (on success)', function() {
    var results = {};
    $(this.el).trigger("upload_success",
                       [{name: "tester's add-on2.xpi"}, results]);
    equals($('#upload-status-text', this.sandbox).text(),
           "Validating tester's add-on2.xpi");
});


module('fileUpload', {
    setup: function() {
        var fxt = this;
        this.sandbox = tests.createSandbox('#file-upload-template');
        initUploadControls();
        this.uploadFile = window.uploadFile;
        this.uploadFileCalled = false;
        // stub out the XHR calls:
        window.uploadFile = function() {
            fxt.uploadFileCalled = true;
            return null;
        };
    },
    teardown: function() {
        this.sandbox.remove();
        window.uploadFile = this.uploadFile;
    }
});

module('preview_edit', {
    setup: function() {
        this.sandbox = tests.createSandbox('#preview-list');
        initUploadPreview();
    },
    teardown: function() {
        this.sandbox.remove();
    }
});

test('Clicking delete screenshot marks checkbox.', function() {
    // $.fx.off sets all animation durations to 0
    $.fx.off = true;
    $(".edit-previews-text a.remove", this.sandbox).trigger('click');
    equals($(".delete input", this.sandbox).attr("checked"), true);
    equals($(".preview:visible", this.sandbox).length, 0);
    $.fx.off = false;
});


module('addon platform chooser', {
    setup: function() {
        this.sandbox = tests.createSandbox('#addon-platform-chooser');
    },
    teardown: function() {
        this.sandbox.remove();
    },
    check: function(sel) {
        $(sel, this.sandbox).attr('checked',true);
        $(sel, this.sandbox).trigger('change');
    }
});

test('platforms > ALL', function() {
    // Check some platforms:
    this.check('input[value="2"]');
    this.check('input[value="3"]');
    // Check ALL platforms:
    this.check('input[value="1"]');
    equals($('input[value="2"]', this.sandbox).attr('checked'), false);
    equals($('input[value="3"]', this.sandbox).attr('checked'), false);
});

test('ALL > platforms', function() {
    // Check ALL platforms:
    this.check('input[value="1"]');
    // Check any other platform:
    this.check('input[value="2"]');
    equals($('input[value="1"]', this.sandbox).attr('checked'), false);
});

test('mobile / desktop', function() {
    // Check ALL desktop platforms:
    this.check('input[value="1"]');
    // Check ALL mobile platforms:
    this.check('input[value="9"]');
    // desktop platforms are still checked:
    equals($('input[value="1"]', this.sandbox).attr('checked'), true);
});

test('mobile > ALL', function() {
    // Check ALL mobile platforms:
    this.check('input[value="9"]');
    // Check Android:
    this.check('input[value="7"]');
    // ALL mobile is no longer checked:
    equals($('input[value="9"]', this.sandbox).attr('checked'), false);
});

test('ALL > mobile', function() {
    // Check Android, Maemo:
    this.check('input[value="7"]');
    this.check('input[value="8"]');
    // Check ALL mobile platforms:
    this.check('input[value="9"]');
    // Specific platforms are no longer checked:
    equals($('input[value="7"]', this.sandbox).attr('checked'), false);
    equals($('input[value="8"]', this.sandbox).attr('checked'), false);
});


module('slugified fields', {
    setup: function() {
        this.sandbox = tests.createSandbox('#slugified-field');
    },
    teardown: function() {
        this.sandbox.remove();
    }
});

asyncTest('non-customized', function() {
    load_unicode();
    tests.waitFor(function() {
        return z == null || z.unicode_letters;
    }).thenDo(function() {
        $("#id_name").val("password exporter");
        slugify();
        equals($("#id_slug").val(), 'password-exporter');
        $("#id_name").val("password exporter2");
        slugify();
        equals($("#id_slug").val(), 'password-exporter2');
        start();
    });
});

asyncTest('customized', function() {
    load_unicode();
    tests.waitFor(function() {
        return z == null || z.unicode_letters;
    }).thenDo(function() {
        $("#id_name").val("password exporter");
        slugify();
        equals($("#id_slug").val(), 'password-exporter');
        $("#id_slug").attr("data-customized", 1);
        $("#id_name").val("password exporter2");
        slugify();
        equals($("#id_slug").val(), 'password-exporter');
        start();
    });
});


module('exclude platforms', {
    setup: function() {
        this._FormData = z.FormData;
        z.FormData = tests.StubOb(z.FormData, {
            send: function() {}
        });
        this.sandbox = tests.createSandbox('#addon-platform-exclusion');

        $.fx.off = true;

        $('#upload-file-input', this.sandbox).addonUploader();

        this.el = $('#upload-file-input', this.sandbox)[0];
        this.el.files = [{
            size: 200,
            name: 'some-addon.xpi'
        }];

        $(this.el).trigger('change');
    },
    teardown: function() {
        this.sandbox.remove();
        z.FormData = this._FormData;
    }
});

test('mobile', function() {
    var sb = this.sandbox;
    results = {
        validation: {
            "errors": 0,
            "detected_type": "mobile",
            "success": true,
            "warnings": 0,
            "notices": 0,
            "message_tree": {},
            "messages": [],
            "rejected": false
        },
        // exclude all but mobile:
        platforms_to_exclude: ['1', '2', '3', '5']
    };

    $(this.el).trigger("upload_success_results",
                       [{name: 'somefile.txt'}, results]);

    // All desktop platforms disabled:
    equals($('.desktop-platforms input:eq(0)', sb).attr('disabled'), true);
    equals($('.desktop-platforms input:eq(1)', sb).attr('disabled'), true);
    equals($('.desktop-platforms input:eq(2)', sb).attr('disabled'), true);
    equals($('.desktop-platforms input:eq(3)', sb).attr('disabled'), true);
    equals($('.desktop-platforms label:eq(0)', sb).hasClass('platform-disabled'),
           true);

    ok($('.platform ul.errorlist', sb).length > 0, 'Message shown to user');

    // All mobile platforms not disabled:
    equals($('.mobile-platforms input:eq(0)', sb).attr('disabled'), false);
    equals($('.mobile-platforms input:eq(1)', sb).attr('disabled'), false);
    equals($('.mobile-platforms input:eq(2)', sb).attr('disabled'), false);
});

test('existing platforms', function() {
    var sb = this.sandbox;
    results = {
        validation: {
            "errors": 0,
            "detected_type": "extension",
            "success": true,
            "warnings": 0,
            "notices": 0,
            "message_tree": {},
            "messages": [],
            "rejected": false
        },
        // exclude one platform as if this version already fulfilled it
        platforms_to_exclude: ['2']
    };

    $(this.el).trigger("upload_success_results",
                       [{name: 'somefile.txt'}, results]);

    equals($('.desktop-platforms input:eq(0)', sb).attr('disabled'), false);
    equals($('.desktop-platforms input:eq(1)', sb).attr('disabled'), true);
    equals($('.desktop-platforms label:eq(0)', sb).hasClass('platform-disabled'),
           false);
});


});
