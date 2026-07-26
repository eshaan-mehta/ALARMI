"""Async processing pipeline: enqueue an uploaded design (``queue``) and run the
extraction job off the request (``worker``). The IFC work itself is the seam in
``app/ifc/processor.py`` that the processing team fills.
"""
