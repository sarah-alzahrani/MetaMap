from flask import Flask, request, render_template, send_file, Response, redirect, url_for
from datetime import datetime
import os
import time

app = Flask(__name__)

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


@app.route('/success', methods=['POST'])
def success():
    if request.method == 'POST':
        file = request.files['file']

        # Save the file with the original name
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Record the start time for this participant
        participant_id = request.form.get('participant_id')
        participant_times[participant_id] = time.time()

        # Read the content of the uploaded file
        with open(filename, 'r') as rdf_file:
            file_content = rdf_file.read()
        # Extract the uploaded file name
        uploaded_file_name = file.filename

        # Create an RDF graph and load the uploaded file
        from rdflib import Graph, Namespace  # Moved import statement here
        g = Graph()
        g.parse(filename, format='turtle', publicID=None)

        # Define the namespaces used in the RDF data
        rr = Namespace("http://www.w3.org/ns/r2rml#")
        rml = Namespace("http://semweb.mmlab.be/ns/rml#")

        # Modify the SPARQL query to extract the name and format from the logicalSource for the first TriplesMap
        query = f"""
                    PREFIX rr: <{rr}>
                    PREFIX rml: <{rml}>
                    SELECT ?name ?format
                    WHERE {{
                        ?tm a rr:TriplesMap;
                           rml:logicalSource [ 
                             rml:source ?name;
                             rml:referenceFormulation ?format
                           ].
                    }}
                    """

        result = g.query(query)
        info = list(result)

        # Initialize the variables with default values
        name, format = "N/A", "N/A"

        # Extract the information if available
        if info:
            name, full_format = info[0]
            format = full_format.split('#')[-1]  # Extract the part after the last #

        return render_template(
            'Ack.html',
            file_content=file_content,
            file_name=name,
            reference_formulation=format,
            uploaded_file_name=uploaded_file_name)  # Pass the uploaded file name



  
@app.route('/submit_metadata', methods=['POST'])
def submit_metadata():
    if request.method == 'POST':
        # Retrieve form data, including the previous fields
        fname = request.form['fname']
        lname = request.form['lname']
        background = request.form['background']
        role = request.form['role']
        organization = request.form['organization']
        requirement = request.form['requirement']
        mapping_type = request.form['mappingType']
        mapping_domain = request.form['mappingDomain']
        mapping_assumptions = request.form['mappingAssumptions']
        technical_requirement = request.form['technicalRequirement']
        risks_issues = request.form['risksIssues']
        input_uri = request.form['InputURI']
        input_creator = request.form['InputSource']
        start_date = request.form['StartDate']
        end_date = request.form['EndDate']
        tool = request.form['Tool']
        mapping_method = request.form['MappingMethod']
        mapping_uri = request.form['mappingURI']
        mapping_name = request.form['mappingName']
        mapping_algorithm = request.form['mappingAlgorithm']
        mapping_format = request.form['mappingFormat']
        testing_uri = request.form['testingURI']
        testing_name = request.form['testingName']
        testing_type = request.form['testingType']
        testing_date = request.form['testingDate']
        testing_result = request.form['testingResult']
        publisher_name = request.form['publisherName']
        publisher_source = request.form['publisherSource']
        version_number = request.form['versionNumber']
        version_datetime = request.form['versionDateTime']
        participant_id = request.form.get('participant_id')
      

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

        # Your existing code...
        from rdflib import Graph, Namespace, Literal, URIRef  # Moved import statement here
        g = Graph()
        dcmi = Namespace("http://purl.org/dc/terms/")  # Define the DCMI namespace
        subject_uri = URIRef("http://example.com/mappings/subject")
        foaf = Namespace("http://xmlns.com/foaf/0.1/")
        custom_ns = Namespace("http://example.com/mappings/")

        # Use the correct predicate URI for format
        custom_ns.format = URIRef("http://example.com/mappings/format")

        # Create RDF triples to describe the stakeholder
        g.add((subject_uri, foaf.givenName, Literal(fname)))
        g.add((subject_uri, foaf.familyName, Literal(lname)))
        g.add((subject_uri, foaf.background, Literal(background)))
        g.add((subject_uri, foaf.role, Literal(role)))
        g.add((subject_uri, foaf.organization, Literal(organization)))

        # Create RDF triples to describe the purpose of the mapping
        g.add((subject_uri, custom_ns.requirement, Literal(requirement)))
        g.add((subject_uri, custom_ns.mappingType, Literal(mapping_type)))
        g.add((subject_uri, custom_ns.mappingDomain, Literal(mapping_domain)))
        g.add((subject_uri, custom_ns.mappingAssumptions, Literal(mapping_assumptions)))
        g.add((subject_uri, custom_ns.technicalRequirement, Literal(technical_requirement)))
        g.add((subject_uri, custom_ns.risksIssues, Literal(risks_issues)))

        # Create RDF triples to describe the input file
        g.add((subject_uri, dcmi.source, Literal(input_uri)))
        g.add((subject_uri, dcmi.creator, Literal(input_creator)))

        # Create RDF triples to describe the design of the mapping
        g.add((subject_uri, custom_ns.startDate, Literal(start_date)))
        g.add((subject_uri, custom_ns.endDate, Literal(end_date)))
        g.add((subject_uri, custom_ns.tool, Literal(tool)))
        g.add((subject_uri, custom_ns.mappingMethod, Literal(mapping_method)))

        # Create RDF triples to describe the mapping
        g.add((subject_uri, custom_ns.mappingURI, Literal(mapping_uri)))
        g.add((subject_uri, custom_ns.mappingName, Literal(mapping_name)))
        g.add((subject_uri, custom_ns.mappingAlgorithm, Literal(mapping_algorithm)))
        g.add((subject_uri, custom_ns.mappingFormat, Literal(mapping_format)))

        # Create RDF triples to describe the testing of the mapping
        g.add((subject_uri, custom_ns.testingURI, Literal(testing_uri)))
        g.add((subject_uri, custom_ns.testingName, Literal(testing_name)))
        g.add((subject_uri, custom_ns.testingType, Literal(testing_type)))
        g.add((subject_uri, custom_ns.testingDate, Literal(testing_date)))
        g.add((subject_uri, custom_ns.testingResult, Literal(testing_result)))

        # Create RDF triples to describe the maintenance of the mapping
        g.add((subject_uri, custom_ns.publisherName, Literal(publisher_name)))
        g.add((subject_uri, custom_ns.publisherSource, Literal(publisher_source)))
        g.add((subject_uri, custom_ns.versionNumber, Literal(version_number)))
        g.add((subject_uri, custom_ns.versionDateTime, Literal(version_datetime)))

        # Serialize RDF data (e.g., to Turtle format)
        rdf_data = g.serialize(format='turtle')

        # Generate a unique filename for the RDF data (e.g., using a timestamp)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        duration_suffix = f"_{int(duration)}s" if duration is not None else ""  # Add duration if available
        rdf_filename = f"metadata_{timestamp}{duration_suffix}.ttl"

        # Save the RDF data to a file on Replit's virtual filesystem
        with open(rdf_filename, "w") as file:
            file.write(rdf_data)

        # Provide the path to the saved file for downloading
        rdf_data_path = rdf_filename

        # Render the success.html template directly
        return render_template('success.html', rdf_data_path=rdf_data_path)


@app.route('/download_rdf')
def download_rdf():
    rdf_data_path = request.args.get('rdf_data_path')

    if rdf_data_path is not None:
        # Generate a unique filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_name = f"metadata_{timestamp}.ttl"

        return send_file(rdf_data_path,
                         as_attachment=True,
                         mimetype='text/turtle',
                         download_name=download_name)
    else:
        return "RDF data is not available for download."


@app.route('/download_rdf_star')
def download_rdf_star():
    rdf_star_data_path = request.args.get('rdf_star_data_path')

    if rdf_star_data_path is not None:
        # Generate a unique filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_name = f"metadata_rdf_star_{timestamp}.ttl"

        return send_file(rdf_star_data_path,
                         as_attachment=True,
                         mimetype='text/turtle',
                         download_name=download_name)
    else:
        return "RDF-Star data is not available for download."


@app.route('/view_rdf')
def view_rdf():
    rdf_data_path = request.args.get('rdf_data_path')

    if rdf_data_path is not None:
        # Load the RDF data from the file and display it
        with open(rdf_data_path, "r") as rdf_file:
            rdf_content = rdf_file.read()

        # You can format and display the RDF content in your desired way
        return Response(rdf_content, mimetype="text/turtle")
    else:
        return "RDF data is not available for viewing."


@app.route('/view_rdf_star')
def view_rdf_star():
    rdf_star_data_path = request.args.get('rdf_star_data_path')

    if rdf_star_data_path is not None:
        # Load the RDF-Star data from the file and display it 
        with open(rdf_star_data_path, "r") as rdf_star_file:
            rdf_star_content = rdf_star_file.read()
        # You can format and display the RDF-Star content in your desired way
        return Response(rdf_star_content, mimetype="text/turtle")
    else:
        return "RDF-Star data is not available for viewing."


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False)
