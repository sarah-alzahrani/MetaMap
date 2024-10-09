import os
import time
from datetime import datetime
from flask import Flask, Response, render_template, request, send_file, session, flash
from rdflib import Graph, Literal, Namespace, URIRef, RDF, BNode
import requests
from rdflib.util import guess_format
import logging
import random
import string
import csv
app = Flask(__name__)

# Set the secret key for sessions
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Set the upload folder path
app.config['UPLOAD_FOLDER'] = 'upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/')
def main():
    return render_template('home.html')


@app.route('/task_explanation')
def task_explanation():
    return render_template('task_explanation.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        participant_id = request.form.get('participant_id')

        # Get file extension
        filename = file.filename
        file_extension = filename.rsplit('.', 1)[1].lower()

        # Handle RDF files
        if file_extension in ['ttl', 'rdf', 'xml']:
            try:
                # Guess RDF format
                rdf_format = guess_format(filename)
                if rdf_format is None:
                    flash('Uploaded file is not a valid RDF format.')
                    return render_template('upload.html', participant_id=participant_id)

                # Save the RDF file
                saved_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(saved_file_path)

                # Parse the RDF file
                g = Graph()
                g.parse(saved_file_path, format=rdf_format)

                # Successfully parsed the RDF file
                session['start_time'] = time.time()
                session['participant_id'] = participant_id

                # Store file content for display
                with open(saved_file_path, 'r', encoding='utf-8') as rdf_file:
                    file_content = rdf_file.read()

                # Extract metadata if needed (optional)
                # You can add more logic here to extract RDF metadata from the parsed graph

                session['file_content'] = file_content
                session['uploaded_file_name'] = file.filename
                return render_template('Ack.html', file_content=file_content, uploaded_file_name=file.filename, participant_id=participant_id)

            except Exception as e:
                # Catch any RDF parsing errors and flash a message
                flash(f'Failed to parse RDF file: {str(e)}')
                logging.error(f"Failed to parse RDF file {filename}: {e}")
                return render_template('upload.html', participant_id=participant_id)

        # Handle SPARQL query (.rq) files
        elif file_extension == 'rq':
            try:
                # Save and display SPARQL query content
                file_content = file.read().decode('utf-8')
                saved_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                with open(saved_file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)

                session['start_time'] = time.time()
                session['participant_id'] = participant_id
                session['file_content'] = file_content
                session['uploaded_file_name'] = file.filename

                return render_template('Ack.html', file_content=file_content, uploaded_file_name=file.filename, participant_id=participant_id)

            except Exception as e:
                flash(f'Failed to handle SPARQL query: {str(e)}')
                logging.error(f"Failed to process SPARQL query {filename}: {e}")
                return render_template('upload.html', participant_id=participant_id)

        else:
            # Unsupported file type
            flash('File type not allowed. Please upload RDF, XML, or SPARQL query (.rq) files.')
            return redirect(request.url)

    return render_template('upload.html')



@app.route('/submit_metadata', methods=['POST'])
def submit_metadata():
    if request.method == 'POST':
        form_data = request.form

        # Store the list of all previously generated codes to ensure uniqueness
        generated_codes = set()

        # Generate a unique random code with 3 digits and 1 uppercase letter
        def generate_random_code():
            while True:
                digits = ''.join(random.choices(string.digits,
                                                k=3))  # 3 random digits
                letter = random.choice(
                    string.ascii_uppercase)  # 1 random uppercase letter
                code = digits + letter  # Combine the digits and letter

                if code not in generated_codes:
                    generated_codes.add(code)
                    return code

        # Generate the code and store it in session
        unique_code = generate_random_code()
        session['unique_code'] = unique_code

        participant_id = session.get('participant_id')
        uploaded_file_name = session.get('uploaded_file_name')

        end_time = time.time()
        start_time = session.get('start_time')
        if start_time:
            duration = end_time - start_time
        else:
            duration = None

        logging.debug(
            f"Participant {participant_id} took {duration} seconds to complete."
        )

        g_named_graph = Graph()
        g_rdf_star = Graph()

        populate_named_graph(form_data, g_named_graph)
        rdf_filename_rdf_star = populate_rdf_star(form_data, g_rdf_star,
                                                  uploaded_file_name)

        rdf_data_named_graph = g_named_graph.serialize(format='turtle')

        timestamp = time.strftime("%Y%m%d%H%M%S")
        duration_suffix = f"_{int(duration)}s" if duration is not None else ""

        rdf_filename_named_graph = f"metadata_named_graph_{timestamp}{duration_suffix}.ttl"
        rdf_named_graph_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                            rdf_filename_named_graph)

        with open(rdf_named_graph_path, "w") as file_named_graph:
            file_named_graph.write(rdf_data_named_graph)

        # Pass the paths for viewing or downloading
        return render_template('success.html',
                               rdf_data_path_named_graph=rdf_named_graph_path,
                               rdf_data_path_rdf_star=rdf_filename_rdf_star,
                               unique_code=unique_code)


def populate_named_graph(form_data, g_named_graph):
    dcmi = Namespace("http://purl.org/dc/terms/")
    subject_uri = URIRef("http://example.com/metag/subject")
    foaf = Namespace("http://xmlns.com/foaf/0.1/")
    custom_ns = Namespace("http://example.com/metag/")
    g_named_graph.bind("metag", custom_ns)
    g_named_graph.bind("foaf", foaf)
    g_named_graph.bind("dcmi", dcmi)

    g_named_graph.add(
        (subject_uri, foaf.givenName, Literal(form_data['fname'])))
    g_named_graph.add(
        (subject_uri, foaf.familyName, Literal(form_data['lname'])))
    g_named_graph.add(
        (subject_uri, foaf.background, Literal(form_data['background'])))
    g_named_graph.add((subject_uri, foaf.role, Literal(form_data['role'])))
    g_named_graph.add(
        (subject_uri, foaf.organization, Literal(form_data['organization'])))

    g_named_graph.add(
        (subject_uri, custom_ns.purpose, Literal(form_data['requirement'])))
    g_named_graph.add((subject_uri, custom_ns.mappingType,
                       Literal(form_data['mappingType'])))
    g_named_graph.add((subject_uri, custom_ns.mappingDomain,
                       Literal(form_data['mappingDomain'])))
    g_named_graph.add((subject_uri, custom_ns.mappingAssumptions,
                       Literal(form_data['mappingAssumptions'])))
    g_named_graph.add((subject_uri, custom_ns.technicalRequirement,
                       Literal(form_data['technicalRequirement'])))
    g_named_graph.add((subject_uri, custom_ns.risksIssues,
                       Literal(form_data['risksIssues'])))

    g_named_graph.add(
        (subject_uri, dcmi.source, Literal(form_data['InputURI'])))
    g_named_graph.add(
        (subject_uri, dcmi.creator, Literal(form_data['InputSource'])))

    g_named_graph.add(
        (subject_uri, custom_ns.startDate, Literal(form_data['StartDate'])))
    g_named_graph.add(
        (subject_uri, custom_ns.endDate, Literal(form_data['EndDate'])))
    g_named_graph.add(
        (subject_uri, custom_ns.tool, Literal(form_data['Tool'])))
    g_named_graph.add((subject_uri, custom_ns.mappingMethod,
                       Literal(form_data['MappingMethod'])))

    g_named_graph.add(
        (subject_uri, custom_ns.mappingURI, Literal(form_data['mappingURI'])))
    g_named_graph.add((subject_uri, custom_ns.mappingName,
                       Literal(form_data['mappingName'])))
    g_named_graph.add((subject_uri, custom_ns.mappingAlgorithm,
                       Literal(form_data['mappingAlgorithm'])))
    g_named_graph.add((subject_uri, custom_ns.mappingFormat,
                       Literal(form_data['mappingFormat'])))

    g_named_graph.add(
        (subject_uri, custom_ns.testingURI, Literal(form_data['testingURI'])))
    g_named_graph.add((subject_uri, custom_ns.testingName,
                       Literal(form_data['testingName'])))
    g_named_graph.add((subject_uri, custom_ns.testingType,
                       Literal(form_data['testingType'])))
    g_named_graph.add((subject_uri, custom_ns.testingDate,
                       Literal(form_data['testingDate'])))
    g_named_graph.add((subject_uri, custom_ns.testingResult,
                       Literal(form_data['testingResult'])))

    g_named_graph.add((subject_uri, custom_ns.publisherName,
                       Literal(form_data['publisherName'])))
    g_named_graph.add((subject_uri, custom_ns.publisherSource,
                       Literal(form_data['publisherSource'])))
    g_named_graph.add((subject_uri, custom_ns.versionNumber,
                       Literal(form_data['versionNumber'])))
    g_named_graph.add((subject_uri, custom_ns.versionDateTime,
                       Literal(form_data['versionDateTime'])))


def populate_rdf_star(form_data, g_rdf_star, uploaded_file_name):
    # Determine if the file should be handled as Ontologies Alignment, Uplift Mapping, or Interlinking
    mapping_type = form_data['mappingType']

    if mapping_type == "Ontologies Alignment":
        return populate_rdf_star_Ontology(form_data, g_rdf_star, uploaded_file_name)

    elif mapping_type == "Uplift Mapping":
        return populate_rdf_star_Uplift(form_data, g_rdf_star, uploaded_file_name)

    elif mapping_type == "Interlinking":
        return populate_rdf_star_Interlink(form_data, g_rdf_star, uploaded_file_name)


def populate_rdf_star_Interlink(form_data, g_rdf_star, uploaded_file_name):
    # Define namespaces for metadata and interlinking-related properties
    custom_ns = Namespace("http://example.com/ontology#")
    dcmi = Namespace("http://purl.org/dc/terms/")
    ex = Namespace("http://example.com/")
    xsd = Namespace("http://www.w3.org/2001/XMLSchema#")

    # Bind namespaces to the graph (optional but recommended)
    g_rdf_star.bind("custom", custom_ns)
    g_rdf_star.bind("dcmi", dcmi)
    g_rdf_star.bind("ex", ex)
    g_rdf_star.bind("xsd", xsd)

    # File path for the uploaded file
    uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file_name)

    if uploaded_file_name.endswith('.rq'):
        # Handle SPARQL files manually as plain text
        with open(uploaded_file_path, 'r', encoding='utf-8') as f:
            sparql_query_content = f.read()  # Read the SPARQL content

        # Create an IRI for the interlinking operation based on the file name
        interlink_iri = URIRef(f"http://example.com/interlink/{uploaded_file_name}")

        # Add SPARQL query content to the RDF-star output
        rdf_star_output = f"{interlink_iri.n3()} a {custom_ns.SPARQLQuery.n3()} ;\n"
        rdf_star_output += f"    {ex.queryContent.n3()} {Literal(sparql_query_content).n3()} .\n\n"

        # Metadata from the form
        fname = form_data.get('fname')
        lname = form_data.get('lname')
        background = form_data.get('background')
        role = form_data.get('role')
        organization = form_data.get('organization')
        requirement = form_data.get('requirement')
        mappingType = form_data.get('mappingType')
        mappingDomain = form_data.get('mappingDomain')
        mappingAssumptions = form_data.get('mappingAssumptions')
        technicalRequirement = form_data.get('technicalRequirement')
        risksIssues = form_data.get('risksIssues')
        inputURI = form_data.get('InputURI')
        inputSource = form_data.get('InputSource')
        startDate = form_data.get('StartDate')
        endDate = form_data.get('EndDate')
        tool = form_data.get('Tool')
        mappingMethod = form_data.get('MappingMethod')
        mappingURI = form_data.get('mappingURI')
        mappingName = form_data.get('mappingName')
        mappingAlgorithm = form_data.get('mappingAlgorithm')
        mappingFormat = form_data.get('mappingFormat')
        testingURI = form_data.get('testingURI')
        testingName = form_data.get('testingName')
        testingType = form_data.get('testingType')
        testingDate = form_data.get('testingDate')
        testingResult = form_data.get('testingResult')
        publisherName = form_data.get('publisherName')
        publisherSource = form_data.get('publisherSource')
        versionNumber = form_data.get('versionNumber')
        versionDateTime = form_data.get('versionDateTime')

        # Annotate the SPARQL query with RDF-star
        rdf_star_output += f"<< {interlink_iri.n3()} {RDF.type.n3()} {custom_ns.InterlinkingOperation.n3()} >>\n"
        rdf_star_output += f"    {dcmi.creator.n3()} {Literal(f'{fname} {lname}').n3()} ;\n"
        rdf_star_output += f"    {dcmi.purpose.n3()} {Literal(requirement).n3()} ;\n"
        rdf_star_output += f"    {ex.toolUsed.n3()} {Literal(tool).n3()} ;\n"
        rdf_star_output += f"    {dcmi.created.n3()} {Literal(startDate).n3()}^^xsd:date ;\n"
        rdf_star_output += f"    {ex.mappingMethod.n3()} {Literal(mappingMethod).n3()} ;\n"
        rdf_star_output += f"    {ex.mappingDomain.n3()} {Literal(mappingDomain).n3()} ;\n"
        rdf_star_output += f"    {ex.mappingURI.n3()} {Literal(mappingURI).n3()} ;\n"
        rdf_star_output += f"    {ex.mappingName.n3()} {Literal(mappingName).n3()} ;\n"
        rdf_star_output += f"    {ex.mappingAlgorithm.n3()} {Literal(mappingAlgorithm).n3()} ;\n"
        rdf_star_output += f"    {ex.mappingFormat.n3()} {Literal(mappingFormat).n3()} ;\n"
        rdf_star_output += f"    {ex.testingURI.n3()} {Literal(testingURI).n3()} ;\n"
        rdf_star_output += f"    {ex.testingName.n3()} {Literal(testingName).n3()} ;\n"
        rdf_star_output += f"    {ex.testingType.n3()} {Literal(testingType).n3()} ;\n"
        rdf_star_output += f"    {ex.testingDate.n3()} {Literal(testingDate).n3()}^^xsd:date ;\n"
        rdf_star_output += f"    {ex.testingResult.n3()} {Literal(testingResult).n3()} ;\n"
        rdf_star_output += f"    {ex.publisherName.n3()} {Literal(publisherName).n3()} ;\n"
        rdf_star_output += f"    {ex.publisherSource.n3()} {Literal(publisherSource).n3()} ;\n"
        rdf_star_output += f"    {ex.versionNumber.n3()} {Literal(versionNumber).n3()} ;\n"
        rdf_star_output += f"    {ex.versionDateTime.n3()} {Literal(versionDateTime).n3()}^^xsd:dateTime .\n\n"

        # Save RDF-star file
        rdf_filename_rdf_star = f"{uploaded_file_name}_rdf_star.ttl"
        rdf_star_file_path = os.path.join(app.config['UPLOAD_FOLDER'], rdf_filename_rdf_star)

        with open(rdf_star_file_path, "w", encoding='utf-8') as file_rdf_star:
            file_rdf_star.write(rdf_star_output)

        logging.debug(f"RDF-star file saved at: {rdf_star_file_path}")

        return rdf_star_file_path

    else:
        # Handle RDF file parsing and annotation as before (non-SPARQL files)
        try:
            g_rdf_star.parse(uploaded_file_path, format='turtle', publicID=None)
        except Exception as e:
            logging.error(f"Failed to parse RDF file {uploaded_file_path}: {e}")
            raise e




    
def populate_rdf_star_Ontology(form_data, g_rdf_star, uploaded_file_name):
    # Parse the ontology alignment file (EDOL alignment file)
    uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file_name)
    g_rdf_star.parse(uploaded_file_path, format='turtle', publicID=None)

    # Define namespaces for metadata and alignment-related namespaces
    foaf = Namespace("http://xmlns.com/foaf/0.1/")
    custom_ns = Namespace("http://example.com/metag/")
    align = Namespace("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#")
    dcmi = Namespace("http://purl.org/dc/terms/")

    # Metadata from the form
    fname = form_data.get('fname')
    lname = form_data.get('lname')
    background = form_data.get('background')
    role = form_data.get('role')
    organization = form_data.get('organization')

    requirement = form_data.get('requirement')
    mappingType = form_data.get('mappingType')
    mappingDomain = form_data.get('mappingDomain')
    mappingAssumptions = form_data.get('mappingAssumptions')
    technicalRequirement = form_data.get('technicalRequirement')
    risksIssues = form_data.get('risksIssues')

    inputURI = form_data.get('InputURI')
    inputSource = form_data.get('InputSource')
    startDate = form_data.get('StartDate')
    endDate = form_data.get('EndDate')
    tool = form_data.get('Tool')
    mappingMethod = form_data.get('MappingMethod')

    mappingURI = form_data.get('mappingURI')
    mappingName = form_data.get('mappingName')
    mappingAlgorithm = form_data.get('mappingAlgorithm')
    mappingFormat = form_data.get('mappingFormat')

    testingURI = form_data.get('testingURI')
    testingName = form_data.get('testingName')
    testingType = form_data.get('testingType')
    testingDate = form_data.get('testingDate')
    testingResult = form_data.get('testingResult')

    publisherName = form_data.get('publisherName')
    publisherSource = form_data.get('publisherSource')
    versionNumber = form_data.get('versionNumber')
    versionDateTime = form_data.get('versionDateTime')

    # Manual RDF-star triples for ontology alignment as output
    rdf_star_output = ""

    # Find the alignment subject and annotate it
    for alignment in g_rdf_star.subjects(RDF.type, align.Alignment):
        # Manually construct RDF-star triples in Turtle format for the whole alignment
        rdf_star_output += f"<< {alignment.n3()} {RDF.type.n3()} {align.Alignment.n3()} >>\n"
        rdf_star_output += f"    {foaf.givenName.n3()} {Literal(fname).n3()} ;\n"
        rdf_star_output += f"    {foaf.familyName.n3()} {Literal(lname).n3()} ;\n"
        rdf_star_output += f"    {foaf.background.n3()} {Literal(background).n3()} ;\n"
        rdf_star_output += f"    {foaf.role.n3()} {Literal(role).n3()} ;\n"
        rdf_star_output += f"    {foaf.organization.n3()} {Literal(organization).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.purpose.n3()} {Literal(requirement).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingType.n3()} {Literal(mappingType).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingDomain.n3()} {Literal(mappingDomain).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingAssumptions.n3()} {Literal(mappingAssumptions).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.technicalRequirement.n3()} {Literal(technicalRequirement).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.risksIssues.n3()} {Literal(risksIssues).n3()} ;\n"
        rdf_star_output += f"    {dcmi.source.n3()} {Literal(inputURI).n3()} ;\n"
        rdf_star_output += f"    {dcmi.creator.n3()} {Literal(inputSource).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.startDate.n3()} {Literal(startDate).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.endDate.n3()} {Literal(endDate).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.tool.n3()} {Literal(tool).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingMethod.n3()} {Literal(mappingMethod).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingURI.n3()} {Literal(mappingURI).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingName.n3()} {Literal(mappingName).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingAlgorithm.n3()} {Literal(mappingAlgorithm).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingFormat.n3()} {Literal(mappingFormat).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingURI.n3()} {Literal(testingURI).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingName.n3()} {Literal(testingName).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingType.n3()} {Literal(testingType).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingDate.n3()} {Literal(testingDate).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingResult.n3()} {Literal(testingResult).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.publisherName.n3()} {Literal(publisherName).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.publisherSource.n3()} {Literal(publisherSource).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.versionNumber.n3()} {Literal(versionNumber).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.versionDateTime.n3()} {Literal(versionDateTime).n3()} .\n\n"

    # Serialize the RDF-star graph to Turtle format and append the manual RDF-star triples
    rdf_data_rdf_star = g_rdf_star.serialize(format='turtle')
    rdf_data_rdf_star += rdf_star_output  # Append the manually constructed RDF-star triples

    rdf_filename_rdf_star = f"{uploaded_file_name}_rdf_star.ttl"
    rdf_star_file_path = os.path.join(app.config['UPLOAD_FOLDER'], rdf_filename_rdf_star)

    with open(rdf_star_file_path, "w") as file_rdf_star:
        file_rdf_star.write(rdf_data_rdf_star)

    logging.debug(f"RDF-star file saved at: {rdf_star_file_path}")

    return rdf_star_file_path

    
def populate_rdf_star_Uplift(form_data, g_rdf_star, uploaded_file_name):
    # Load the RML mapping file (your mapping file)
    uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file_name)
    g_rdf_star.parse(uploaded_file_path, format='turtle', publicID=None)

    # Define namespaces for metadata and the RML/RR namespaces
    foaf = Namespace("http://xmlns.com/foaf/0.1/")
    custom_ns = Namespace("http://example.com/metag/")
    dcmi = Namespace("http://purl.org/dc/terms/")
    rr = Namespace("http://www.w3.org/ns/r2rml#")

    # Metadata from the form
    fname = form_data.get('fname')
    lname = form_data.get('lname')
    background = form_data.get('background')
    role = form_data.get('role')
    organization = form_data.get('organization')

    requirement = form_data.get('requirement')
    mappingType = form_data.get('mappingType')
    mappingDomain = form_data.get('mappingDomain')
    mappingAssumptions = form_data.get('mappingAssumptions')
    technicalRequirement = form_data.get('technicalRequirement')
    risksIssues = form_data.get('risksIssues')

    inputURI = form_data.get('InputURI')
    inputSource = form_data.get('InputSource')
    startDate = form_data.get('StartDate')
    endDate = form_data.get('EndDate')
    tool = form_data.get('Tool')
    mappingMethod = form_data.get('MappingMethod')

    mappingURI = form_data.get('mappingURI')
    mappingName = form_data.get('mappingName')
    mappingAlgorithm = form_data.get('mappingAlgorithm')
    mappingFormat = form_data.get('mappingFormat')

    testingURI = form_data.get('testingURI')
    testingName = form_data.get('testingName')
    testingType = form_data.get('testingType')
    testingDate = form_data.get('testingDate')
    testingResult = form_data.get('testingResult')

    publisherName = form_data.get('publisherName')
    publisherSource = form_data.get('publisherSource')
    versionNumber = form_data.get('versionNumber')
    versionDateTime = form_data.get('versionDateTime')

    # Manual RDF-star triples as output
    rdf_star_output = ""

    # Iterate through the TriplesMap subjects in the RML file and annotate them
    for tm in g_rdf_star.subjects(RDF.type, rr.TriplesMap):
        # Manually construct RDF-star triples in Turtle format
        rdf_star_output += f"<< {tm.n3()} {RDF.type.n3()} {rr.TriplesMap.n3()} >>\n"
        rdf_star_output += f"    {foaf.givenName.n3()} {Literal(fname).n3()} ;\n"
        rdf_star_output += f"    {foaf.familyName.n3()} {Literal(lname).n3()} ;\n"
        rdf_star_output += f"    {foaf.background.n3()} {Literal(background).n3()} ;\n"
        rdf_star_output += f"    {foaf.role.n3()} {Literal(role).n3()} ;\n"
        rdf_star_output += f"    {foaf.organization.n3()} {Literal(organization).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.purpose.n3()} {Literal(requirement).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingType.n3()} {Literal(mappingType).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingDomain.n3()} {Literal(mappingDomain).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingAssumptions.n3()} {Literal(mappingAssumptions).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.technicalRequirement.n3()} {Literal(technicalRequirement).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.risksIssues.n3()} {Literal(risksIssues).n3()} ;\n"
        rdf_star_output += f"    {dcmi.source.n3()} {Literal(inputURI).n3()} ;\n"
        rdf_star_output += f"    {dcmi.creator.n3()} {Literal(inputSource).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.startDate.n3()} {Literal(startDate).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.endDate.n3()} {Literal(endDate).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.tool.n3()} {Literal(tool).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingMethod.n3()} {Literal(mappingMethod).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingURI.n3()} {Literal(mappingURI).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingName.n3()} {Literal(mappingName).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingAlgorithm.n3()} {Literal(mappingAlgorithm).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.mappingFormat.n3()} {Literal(mappingFormat).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingURI.n3()} {Literal(testingURI).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingName.n3()} {Literal(testingName).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingType.n3()} {Literal(testingType).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingDate.n3()} {Literal(testingDate).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.testingResult.n3()} {Literal(testingResult).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.publisherName.n3()} {Literal(publisherName).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.publisherSource.n3()} {Literal(publisherSource).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.versionNumber.n3()} {Literal(versionNumber).n3()} ;\n"
        rdf_star_output += f"    {custom_ns.versionDateTime.n3()} {Literal(versionDateTime).n3()} .\n\n"

    # Serialize the RDF-star graph to Turtle format and append the manual RDF-star triples
    rdf_data_rdf_star = g_rdf_star.serialize(format='turtle')
    rdf_data_rdf_star += rdf_star_output  # Append the manually constructed RDF-star triples

    rdf_filename_rdf_star = f"{uploaded_file_name}_rdf_star.ttl"
    rdf_star_file_path = os.path.join(app.config['UPLOAD_FOLDER'], rdf_filename_rdf_star)

    with open(rdf_star_file_path, "w") as file_rdf_star:
        file_rdf_star.write(rdf_data_rdf_star)

    logging.debug(f"RDF-star file saved at: {rdf_star_file_path}")

    return rdf_star_file_path

@app.route('/view_metadata')
def view_metadata():
    rdf_data_path = request.args.get('rdf_data_path')
    rdf_star_data_path = request.args.get('rdf_star_data_path')

    if rdf_data_path:
        logging.debug(f"Viewing RDF named graph data at: {rdf_data_path}")
        with open(rdf_data_path, "r") as rdf_file:
            rdf_content = rdf_file.read()
        return Response(rdf_content, mimetype="text/turtle")
    elif rdf_star_data_path:
        logging.debug(f"Viewing RDF-star data at: {rdf_star_data_path}")
        with open(rdf_star_data_path, "r") as rdf_star_file:
            rdf_star_content = rdf_star_file.read()
        return Response(rdf_star_content, mimetype="text/turtle")
    else:
        return "RDF data is not available for viewing."


@app.route('/download_metadata')
def download_metadata():
    rdf_data_path = request.args.get('rdf_data_path')
    rdf_star_data_path = request.args.get('rdf_star_data_path')

    if rdf_data_path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_name = f"metadata_named_graph_{timestamp}.ttl"
        return send_file(rdf_data_path,
                         as_attachment=True,
                         mimetype='text/turtle',
                         download_name=download_name)
    elif rdf_star_data_path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_name = f"metadata_rdf_star_{timestamp}.ttl"
        return send_file(rdf_star_data_path,
                         as_attachment=True,
                         mimetype='text/turtle',
                         download_name=download_name)
    else:
        return "RDF data is not available for download."


# Function to save code, user ID, and timestamp to CSV
def save_code_to_csv(code, user_id, filename='codes.csv'):
    file_exists = os.path.isfile(filename)  # Check if the file already exists
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'user_id', 'code']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If file doesn't exist, write the header first
        if not file_exists:
            writer.writeheader()

        # Write the data
        writer.writerow({
            'timestamp':
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id':
            user_id,
            'code':
            code
        })


@app.route('/sparql', methods=['GET', 'POST'])
def sparql():
    if request.method == 'POST':
        query = request.form['query']
        headers = {"Content-Type": "application/sparql-query"}
        response = requests.post(GRAPHDB_URL, data=query, headers=headers)
        return response.text
    return render_template('sparql.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)
