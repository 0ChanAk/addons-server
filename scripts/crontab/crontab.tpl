MAILTO=amo-developers@mozilla.org

HOME=/tmp

# Every minute!
* * * * * {{ z_cron }} fast_current_version
* * * * * {{ z_cron }} migrate_collection_users

# Every 30 minutes.
*/30 * * * * {{ z_cron }} tag_jetpacks
*/30 * * * * {{ z_cron }} update_addons_current_version
*/30 * * * * {{ z_cron }} reset_featured_addons
*/30 * * * * {{ z_cron }} cleanup_watermarked_file

#once per hour
5 * * * * {{ z_cron }} update_collections_subscribers
10 * * * * {{ z_cron }} update_blog_posts
20 * * * * {{ z_cron }} addon_last_updated
25 * * * * {{ z_cron }} update_collections_votes
40 * * * * {{ z_cron }} fetch_ryf_blog
45 * * * * {{ z_cron }} update_addon_appsupport
50 * * * * {{ z_cron }} cleanup_extracted_file
55 * * * * {{ z_cron }} unhide_disabled_files


#every 3 hours
20 */3 * * * {{ z_cron }} compatibility_report
# clouserw commented this out
#20 */3 * * * {{ remora }}; php -f compatibility_report.php

#every 4 hours
40 */4 * * * {{ django }} clean_redis

#twice per day
25 1,13 * * * {{ remora }}; {{ python }} import-personas.py
# Add slugs after we get all the new personas.
25 2,14 * * * {{ z_cron }} addons_add_slugs
45 2,14 * * * {{ z_cron }} give_personas_versions
25 8,20 * * * {{ z_cron }} update_collections_total
25 9,21 * * * {{ z_cron }} hide_disabled_files

#once per day
05 0 * * * {{ z_cron }} email_daily_ratings --settings=settings_local_mkt
30 1 * * * {{ z_cron }} update_user_ratings
40 1 * * * {{ z_cron }} update_weekly_downloads
50 1 * * * {{ z_cron }} gc
45 1 * * * {{ z_cron }} mkt_gc --settings=settings_local_mkt
30 2 * * * {{ z_cron }} mail_pending_refunds --settings=settings_local_mkt
45 2 * * * {{ django }} process_addons --task=update_manifests --settings=settings_local_mkt
30 3 * * * {{ django }} cleanup
30 4 * * * {{ z_cron }} cleanup_synced_collections
30 5 * * * {{ z_cron }} expired_resetcode
30 6 * * * {{ z_cron }} category_totals
30 7 * * * {{ z_cron }} collection_subscribers
30 8 * * * {{ z_cron }} personas_adu
30 9 * * * {{ z_cron }} share_count_totals
30 10 * * * {{ z_cron }} recs
30 20 * * * {{ z_cron }} update_perf
30 22 * * * {{ z_cron }} deliver_hotness
40 23 * * * {{ z_cron }} update_compat_info_for_fx4
45 23 * * * {{ django }} dump_apps
55 23 * * * {{ z_cron }} clean_out_addonpremium

#Once per day after 2100 PST (after metrics is done)
35 21 * * * {{ z_cron }} update_addon_download_totals
40 21 * * * {{ z_cron }} weekly_downloads
35 22 * * * {{ z_cron }} update_global_totals
40 22 * * * {{ z_cron }} update_addon_average_daily_users
30 23 * * * {{ z_cron }} index_latest_stats
35 23 * * * {{ z_cron }} index_latest_mkt_stats --settings=settings_local_mkt
45 23 * * * {{ z_cron }} update_addons_collections_downloads

# Once per week
45 23 * * 4 {{ z_cron }} unconfirmed
35 22 * * 3 {{ django }} process_addons --task=check_paypal --settings=settings_local_mkt

MAILTO=root
