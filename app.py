from flask import Flask, request, render_template, send_file, Response
from datetime import datetime
from rdflib import Graph, Namespace, Literal, URIRef
import os
import io
import time

app = Flask(__name__)

# Set the upload folder path
app.config['UPLOAD_FOLDER'] = 'upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

metadata_graph = Graph()  # Create a global metadata graph


@app.route('/')
def main():
    return render_template('home.html')


@app.route('/success', methods=['POST'])
def success():
    if request.method == 'POST':
        file = request.files['file']

        # Save the file with the original name
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

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

# ... (previous code)


# ... (previous code)

@app.route('/submit_metadata', methods=['POST'])
def submit_metadata():
    if request.method == 'POST':
        # Retrieve form data, including the previous fields
        fname = request.form['fname']
        lname = request.form['lname']
        organization = request.form['organization']
        input_uri = request.form['InputURI']
        input_creator = request.form['InputSource']
        start_date = request.form['StartDate']
        end_date = request.form['EndDate']
        tool = request.form['Tool']
        mapping_method = request.form['MappingMethod']
        mapping_type = request.form['MappingType']
        mapping_domain = request.form['MappingDomain']

        # Create an RDF graph
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
        g.add((subject_uri, foaf.organization, Literal(organization)))

        # Create RDF triples to describe the input file
        g.add((subject_uri, custom_ns.format, Literal("Named Graph")))  # Use the custom format as a predicate
        g.add((subject_uri, dcmi.creator, Literal(input_creator)))
        g.add((subject_uri, dcmi.source, Literal(input_uri)))

        # Create RDF triples to describe mapping metadata
        g.add((subject_uri, custom_ns.startDate, Literal(start_date)))
        g.add((subject_uri, custom_ns.endDate, Literal(end_date)))
        g.add((subject_uri, custom_ns.toolUsed, Literal(tool)))
        g.add((subject_uri, custom_ns.mappingMethod, Literal(mapping_method)))
        g.add((subject_uri, custom_ns.mappingType, Literal(mapping_type)))
        g.add((subject_uri, custom_ns.mappingDomain, Literal(mapping_domain)))

        # Serialize RDF data (e.g., to Turtle format)
        rdf_data = g.serialize(format='turtle')

        # Generate a unique filename for the RDF data (e.g., using a timestamp)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        rdf_filename = f"metadata_{timestamp}.ttl"

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
        # Load the RDF data from the file and display it (you can choose how you want to display it)
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
        # Load the RDF-Star data from the file and display it (you can choose how you want to display it)
        with open(rdf_star_data_path, "r") as rdf_star_file:
            rdf_star_content = rdf_star_file.read()

        # You can format and display the RDF-Star content in your desired way
        return Response(rdf_star_content, mimetype="text/turtle")
    else:
        return "RDF-Star data is not available for viewing."

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
