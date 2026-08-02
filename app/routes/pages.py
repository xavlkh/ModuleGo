"""Page routes: home, comparison, bookmarks, reviews dashboards."""

from flask import render_template, request


def serve_index():
    query = request.args.get('q', '')
    return render_template('modules/index.html', query=query)


def serve_comparison():
    return render_template('modules/comparison.html')


def serve_bookmarks():
    return render_template('modules/bookmarks.html')


def serve_reviews():
    return render_template('modules/reviews.html')
