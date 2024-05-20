import os
import time
from datetime import datetime
from flask import Flask, Response, render_template, request, send_file, session
from rdflib import Graph, Literal, Namespace, URIRef, RDF

app = Flask(__name__)

# Set the secret key for sessions
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Set the upload folder path
app.config['UPLOAD_FOLDER'] = 'upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

participant_times = {}  # Dictionary to store participant start times


@app.route('/')
def main():
    return render_template('home.html')


@app.route('/task_explanation')
def task_explanation():
    # Render the task explanation template
    return render_template('task_explanation.html')


# success route
@app.route('/success', methods=['POST'])
def success():
    if request.method == 'POST':
        file = request.files['file']
        participant_id = request.form.get('participant_id')

        # Save the file with the original name
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Record the start time for this participant in session
        session['start_time'] = time.time()
        session['participant_id'] = participant_id

        # Read the content of the uploaded file
        with open(filename, 'r') as rdf_file:
            file_content = rdf_file.read()

        # Extract the uploaded file name
        uploaded_file_name = file.filename

        # Create an RDF graph and load the uploaded file
        g = Graph()
        g.parse(filename, format='turtle', publicID=None)

        # Define the namespaces used in the RDF data
        rr = Namespace("http://www.w3.org/ns/r2rml#")
        rml = Namespace("http://semweb.mmlab.be/ns/rml#")

        # Extract the name and format from the logicalSource for the first TriplesMap
        name = "N/A"
        format = "N/A"
        for tm in g.subjects(RDF.type, rr.TriplesMap):
            logical_source = g.value(tm, rml.logicalSource)
            if logical_source:
                name = g.value(logical_source, rml.source, default="N/A")
                format_uri = g.value(logical_source, rml.referenceFormulation, default="N/A")
                if format_uri:
                    format = format_uri.split('#')[-1]  # Extract the part after the last #
                break

        # Store data in session
        session['file_content'] = file_content
        session['file_name'] = name
        session['reference_formulation'] = format
        session['uploaded_file_name'] = uploaded_file_name

        return render_template('Ack.html',
                               file_content=file_content,
                               file_name=name,
                               reference_formulation=format,
                               uploaded_file_name=uploaded_file_name,
                               participant_id=participant_id)


@app.route('/submit_metadata', methods=['POST'])
def submit_metadata():
    if request.method == 'POST':
        # Retrieve form data
        form_data = request.form

        # Retrieve session data
        participant_id = session.get('participant_id')
        uploaded_file_name = session.get('uploaded_file_name')

        # Record the end time for this participant
        end_time = time.time()

        # Calculate the duration
        start_time = participant_times.get(participant_id)
        if start_time:
            duration = end_time - start_time
        else:
            duration = None  # Handle the case where start time is not recorded

        # Print or log the duration (you can replace print with logging if needed)
        print(f"Participant {participant_id} took {duration} seconds to complete.")

        # Create RDF graphs for both formats
        g_named_graph = Graph()
        g_rdf_star = Graph()

        # Populate RDF graphs for both formats
        populate_named_graph(form_data, g_named_graph)
        populate_rdf_star(form_data, g_rdf_star, uploaded_file_name)

        # Serialize RDF data (e.g., to Turtle format)
        rdf_data_named_graph = g_named_graph.serialize(format='turtle').decode('utf-8')
        rdf_data_rdf_star = g_rdf_star.serialize(format='turtle').decode('utf-8')

        # Generate unique filenames for the RDF data (e.g., using a timestamp)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        duration_suffix = f"_{int(duration)}s" if duration is not None else ""

        rdf_filename_named_graph = f"metadata_named_graph_{timestamp}{duration_suffix}.ttl"
        rdf_filename_rdf_star = f"metadata_rdf_star_{timestamp}{duration_suffix}.ttl"

        # Save the RDF data to files on the virtual filesystem
        with open(rdf_filename_named_graph, "w") as file_named_graph:
            file_named_graph.write(rdf_data_named_graph)

        with open(rdf_filename_rdf_star, "w") as file_rdf_star:
            file_rdf_star.write(rdf_data_rdf_star)

        # Provide the paths to the saved files for downloading
        rdf_data_path_named_graph = rdf_filename_named_graph
        rdf_data_path_rdf_star = rdf_filename_rdf_star

        # Render the results template with paths to both RDF files
        return render_template('success.html',
                               rdf_data_path_named_graph=rdf_data_path_named_graph,
                               rdf_data_path_rdf_star=rdf_data_path_rdf_star)


def populate_named_graph(form_data, g_named_graph):
    dcmi = Namespace("http://purl.org/dc/terms/")  # Define the DCMI namespace
    subject_uri = URIRef("http://example.com/metag/subject")
    foaf = Namespace("http://xmlns.com/foaf/0.1/")
    custom_ns = Namespace("http://example.com/metag/")
    g_named_graph.bind("metag", custom_ns)

    # Create RDF triples to describe the stakeholder
    g_named_graph.add((subject_uri, foaf.givenName, Literal(form_data['fname'])))
    g_named_graph.add((subject_uri, foaf.familyName, Literal(form_data['lname'])))
    g_named_graph.add((subject_uri, foaf.background, Literal(form_data['background'])))
    g_named_graph.add((subject_uri, foaf.role, Literal(form_data['role'])))
    g_named_graph.add((subject_uri, foaf.organization, Literal(form_data['organization'])))

    # Create RDF triples to describe the purpose of the mapping
    g_named_graph.add((subject_uri, custom_ns.purpose, Literal(form_data['requirement'])))
    g_named_graph.add((subject_uri, custom_ns.mappingType, Literal(form_data['mappingType'])))
    g_named_graph.add((subject_uri, custom_ns.mappingDomain, Literal(form_data['mappingDomain'])))
    g_named_graph.add((subject_uri, custom_ns.mappingAssumptions, Literal(form_data['mappingAssumptions'])))
    g_named_graph.add((subject_uri, custom_ns.technicalRequirement, Literal(form_data['technicalRequirement'])))
    g_named_graph.add((subject_uri, custom_ns.risksIssues, Literal(form_data['risksIssues'])))

    # Create RDF triples to describe the input file
    g_named_graph.add((subject_uri, dcmi.source, Literal(form_data['InputURI'])))
    g_named_graph.add((subject_uri, dcmi.creator, Literal(form_data['InputSource'])))

    # Create RDF triples to describe the design of the mapping
    g_named_graph.add((subject_uri, custom_ns.startDate, Literal(form_data['StartDate'])))
    g_named_graph.add((subject_uri, custom_ns.endDate, Literal(form_data['EndDate'])))
    g_named_graph.add((subject_uri, custom_ns.tool, Literal(form_data['Tool'])))
    g_named_graph.add((subject_uri, custom_ns.mappingMethod, Literal(form_data['MappingMethod'])))

    # Create RDF triples to describe the mapping
    g_named_graph.add((subject_uri, custom_ns.mappingURI, Literal(form_data['mappingURI'])))
    g_named_graph.add((subject_uri, custom_ns.mappingName, Literal(form_data['mappingName'])))
    g_named_graph.add((subject_uri, custom_ns.mappingAlgorithm, Literal(form_data['mappingAlgorithm'])))
    g_named_graph.add((subject_uri, custom_ns.mappingFormat, Literal(form_data['mappingFormat'])))

    # Create RDF triples to describe the testing of the mapping
    g_named_graph.add((subject_uri, custom_ns.testingURI, Literal(form_data['testingURI'])))
    g_named_graph.add((subject_uri, custom_ns.testingName, Literal(form_data['testingName'])))
    g_named_graph.add((subject_uri, custom_ns.testingType, Literal(form_data['testingType'])))
    g_named_graph.add((subject_uri, custom_ns.testingDate, Literal(form_data['testingDate'])))
    g_named_graph.add((subject_uri, custom_ns.testingResult, Literal(form_data['testingResult'])))

    # Create RDF triples to describe the maintenance of the mapping
    g_named_graph.add((subject_uri, custom_ns.publisherName, Literal(form_data['publisherName'])))
    g_named_graph.add((subject_uri, custom_ns.publisherSource, Literal(form_data['publisherSource'])))
    g_named_graph.add((subject_uri, custom_ns.versionNumber, Literal(form_data['versionNumber'])))
    g_named_graph.add((subject_uri, custom_ns.versionDateTime, Literal(form_data['versionDateTime'])))


def populate_rdf_star(form_data, g_rdf_star, uploaded_file_name):
    # Load the uploaded file
    uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file_name)
    g_rdf_star.parse(uploaded_file_path, format='turtle', publicID=None)

    # Define namespaces
    rr = Namespace("http://www.w3.org/ns/r2rml#")
    rml = Namespace("http://semweb.mmlab.be/ns/rml#")
    custom_ns = Namespace("http://example.com/metag/")
    dcmi = Namespace("http://purl.org/dc/terms/")
    foaf = Namespace("http://xmlns.com/foaf/0.1/")

    # Prepare the data to be inserted
    input_uri = form_data['InputURI']
    input_source = form_data['InputSource']
    purpose = form_data['requirement']
    mapping_type = form_data['mappingType']
    mapping_domain = form_data['mappingDomain']
    mapping_assumptions = form_data['mappingAssumptions']
    technical_requirement = form_data['technicalRequirement']
    risks_issues = form_data['risksIssues']
    start_date = form_data['StartDate']
    end_date = form_data['EndDate']
    tool = form_data['Tool']
    mapping_method = form_data['MappingMethod']
    mapping_uri = form_data['mappingURI']
    mapping_name = form_data['mappingName']
    mapping_algorithm = form_data['mappingAlgorithm']
    mapping_format = form_data['mappingFormat']
    testing_uri = form_data['testingURI']
    testing_name = form_data['testingName']
    testing_type = form_data['testingType']
    testing_date = form_data['testingDate']
    testing_result = form_data['testingResult']
    publisher_name = form_data['publisherName']
    publisher_source = form_data['publisherSource']
    version_number = form_data['versionNumber']
    version_date_time = form_data['versionDateTime']

    # Add metadata to logicalSource triple
    for logical_source in g_rdf_star.subjects(RDF.type, rml.LogicalSource):
        g_rdf_star.add((logical_source, dcmi.source, Literal(input_uri)))
        g_rdf_star.add((logical_source, dcmi.creator, Literal(input_source)))

    # Add metadata to TriplesMap triple
    for tm in g_rdf_star.subjects(RDF.type, rr.TriplesMap):
        g_rdf_star.add((tm, custom_ns.purpose, Literal(purpose)))
        g_rdf_star.add((tm, custom_ns.mappingType, Literal(mapping_type)))
        g_rdf_star.add((tm, custom_ns.mappingDomain, Literal(mapping_domain)))
        g_rdf_star.add((tm, custom_ns.mappingAssumptions, Literal(mapping_assumptions)))
        g_rdf_star.add((tm, custom_ns.technicalRequirement, Literal(technical_requirement)))
        g_rdf_star.add((tm, custom_ns.risksIssues, Literal(risks_issues)))
        g_rdf_star.add((tm, custom_ns.startDate, Literal(start_date)))
        g_rdf_star.add((tm, custom_ns.endDate, Literal(end_date)))
        g_rdf_star.add((tm, custom_ns.tool, Literal(tool)))
        g_rdf_star.add((tm, custom_ns.mappingMethod, Literal(mapping_method)))
        g_rdf_star.add((tm, custom_ns.mappingURI, Literal(mapping_uri)))
        g_rdf_star.add((tm, custom_ns.mappingName, Literal(mapping_name)))
        g_rdf_star.add((tm, custom_ns.mappingAlgorithm, Literal(mapping_algorithm)))
        g_rdf_star.add((tm, custom_ns.mappingFormat, Literal(mapping_format)))
        g_rdf_star.add((tm, custom_ns.testingURI, Literal(testing_uri)))
        g_rdf_star.add((tm, custom_ns.testingName, Literal(testing_name)))
        g_rdf_star.add((tm, custom_ns.testingType, Literal(testing_type)))
        g_rdf_star.add((tm, custom_ns.testingDate, Literal(testing_date)))
        g_rdf_star.add((tm, custom_ns.testingResult, Literal(testing_result)))
        g_rdf_star.add((tm, custom_ns.publisherName, Literal(publisher_name)))
        g_rdf_star.add((tm, custom_ns.publisherSource, Literal(publisher_source)))
        g_rdf_star.add((tm, custom_ns.versionNumber, Literal(version_number)))
        g_rdf_star.add((tm, custom_ns.versionDateTime, Literal(version_date_time)))


@app.route('/download_metadata')
def download_metadata():
    rdf_data_path = request.args.get('rdf_data_path')
    rdf_star_data_path = request.args.get('rdf_star_data_path')

    if rdf_data_path is not None:
        # Generate a unique filename with a timestamp for named graph
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_name = f"metadata_named_graph_{timestamp}.ttl"
        return send_file(rdf_data_path,
                         as_attachment=True,
                         mimetype='text/turtle',
                         download_name=download_name)
    elif rdf_star_data_path is not None:
        # Generate a unique filename with a timestamp for RDF-Star
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_name = f"metadata_rdf_star_{timestamp}.ttl"
        return send_file(rdf_star_data_path,
                         as_attachment=True,
                         mimetype='text/turtle',
                         download_name=download_name)
    else:
        return "RDF data is not available for download."


@app.route('/view_metadata')
def view_metadata():
    rdf_data_path = request.args.get('rdf_data_path')
    rdf_star_data_path = request.args.get('rdf_star_data_path')

    if rdf_data_path is not None:
        # Load the RDF data from the file and display it for named graph
        with open(rdf_data_path, "r") as rdf_file:
            rdf_content = rdf_file.read()
        return Response(rdf_content, mimetype="text/turtle")
    elif rdf_star_data_path is not None:
        # Load the RDF-Star data from the file and display it
        with open(rdf_star_data_path, "r") as rdf_star_file:
            rdf_star_content = rdf_star_file.read()
        return Response(rdf_star_content, mimetype="text/turtle")
    else:
        return "RDF data is not available for viewing."


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)
