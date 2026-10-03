app_name = "commera_qikink"
app_title = "Qikink"
app_publisher = "Rahul Agrawal"
app_description = "Send Commera orders to Qikink for print on demand"
app_email = "12agrawalrahul@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["commera"]
commera_api_version = [1]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "commera_qikink",
# 		"logo": "/assets/commera_qikink/logo.png",
# 		"title": "Qikink",
# 		"route": "/commera_qikink",
# 		"has_permission": "commera_qikink.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/commera_qikink/css/commera_qikink.css"
# app_include_js = "/assets/commera_qikink/js/commera_qikink.js"

# include js, css files in header of web template
# web_include_css = "/assets/commera_qikink/css/commera_qikink.css"
# web_include_js = "/assets/commera_qikink/js/commera_qikink.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "commera_qikink/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "commera_qikink/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "commera_qikink.utils.jinja_methods",
# 	"filters": "commera_qikink.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "commera_qikink.install.before_install"
# after_install = "commera_qikink.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "commera_qikink.uninstall.before_uninstall"
# after_uninstall = "commera_qikink.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "commera_qikink.utils.before_app_install"
# after_app_install = "commera_qikink.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "commera_qikink.utils.before_app_uninstall"
# after_app_uninstall = "commera_qikink.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "commera_qikink.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "commera_qikink.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["commera_qikink.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"commera_qikink.tasks.all"
# 	],
# 	"daily": [
# 		"commera_qikink.tasks.daily"
# 	],
# 	"hourly": [
# 		"commera_qikink.tasks.hourly"
# 	],
# 	"weekly": [
# 		"commera_qikink.tasks.weekly"
# 	],
# 	"monthly": [
# 		"commera_qikink.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "commera_qikink.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "commera_qikink.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "commera_qikink.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "commera_qikink.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["commera_qikink.utils.before_request"]
# after_request = ["commera_qikink.utils.after_request"]

# Job Events
# ----------
# before_job = ["commera_qikink.utils.before_job"]
# after_job = ["commera_qikink.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"commera_qikink.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


after_install = "commera_qikink.install.add_custom_fields"
after_migrate = "commera_qikink.install.add_custom_fields"

commera_validate_cart = ["commera_qikink.cart.get_unmapped_item_refusal"]
commera_order_paid = ["commera_qikink.orders.on_order_paid"]

doc_events = {"Sales Order": {"before_validate": "commera_qikink.orders.set_drop_ship_lines"}}
